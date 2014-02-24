#!/usr/bin/python3
import yaml, gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11
GObject.threads_init()
Gst.init(None)

class TestSource:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.main = main

        self.src = Gst.ElementFactory.make('videotestsrc', 'videotestsrc-' + name)
        self.main.pipeline.add(self.src)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.src.link(self.tee)


class URISource:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.uri = props['uri']
        self.main = main

        self.src = Gst.ElementFactory.make('uridecodebin', 'uridecodebin-' + name)
        self.main.pipeline.add(self.src)
        self.src.set_property('uri', self.uri)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)

        self.src.connect('pad-added', self.on_pad_added, self.tee)

    def on_pad_added(self, element, srcpad, dest):
        name = srcpad.query_caps(None).to_string()
        print('on_pad_added:', name)
        if name.startswith('video/'):
            sinkpad = dest.get_static_pad('sink')
            srcpad.link(sinkpad)
            print(srcpad.is_linked())


class V4L2Source:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.device = props['device']
        self.main = main

        self.src = Gst.ElementFactory.make('v4l2src', 'v4l2src-' + name)
        self.main.pipeline.add(self.src)
        self.src.set_property('device', self.device)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.src.link(self.tee)


class Processor:
    def __init__(self, source, sink, name, props, main):
        self.source = source
        self.sink = sink
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        caps = Gst.Caps.from_string("video/x-raw")
        caps.set_value('width', int(self.main.settings['resolution'][0]))
        caps.set_value('height', int(self.main.settings['resolution'][1]))
        self.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter-' + name)
        self.main.pipeline.add(self.capsfilter)
        self.capsfilter.set_property('caps', caps)
        self.queue.link(self.capsfilter)

        self.rate = Gst.ElementFactory.make('videorate', 'videorate-' + name)
        self.main.pipeline.add(self.rate)
        self.capsfilter.link(self.rate)

        self.alpha = Gst.ElementFactory.make('alpha', 'alpha-' + name)
        self.main.pipeline.add(self.alpha)
        self.rate.link(self.alpha)

        alphapad = self.alpha.get_static_pad('src')
        self.sinkpad = self.sink.get_compatible_pad(alphapad, None)
        alphapad.link(self.sinkpad)


class SimpleVideoSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue' + name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.autovideosink = Gst.ElementFactory.make('autovideosink', 'autovideosink' + name)
        self.main.pipeline.add(self.autovideosink)
        self.queue.link(self.autovideosink)


class Mixer:
    def __init__(self, name, mixdict, main):
        # Remember - set zorder in videomixer by set_property('zorder', n) on the videomixer pad
        self.name = name
        self.main = main

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.props.homogeneous = False
        self.main.mixersbox.pack_start(self.box, True, True, 4)

        self.label = Gtk.Label()
        self.label.set_markup("<span size='x-large'><b>" + self.name + "</b></span>")
        self.box.pack_start(self.label, False, False, 4)

        self.previewarea = Gtk.DrawingArea()
        self.box.pack_start(self.previewarea, True, True, 8)

        self.videomixer = Gst.ElementFactory.make('videomixer', 'videomixer-' + name)
        self.main.pipeline.add(self.videomixer)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.videomixer.link(self.tee)

        self.previewqueue = Gst.ElementFactory.make('queue', 'previewqueue-' + name)
        self.main.pipeline.add(self.previewqueue)
        self.tee.link(self.previewqueue)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + name)
        self.main.pipeline.add(self.videoconvert)
        self.previewqueue.link(self.videoconvert)

        self.previewsink = Gst.ElementFactory.make('xvimagesink', 'previewsink-' + name)
        self.main.pipeline.add(self.previewsink)
        self.videoconvert.link(self.previewsink)

        self.sources = {}
        self.processors = {}
        for source in mixdict['sources']:
            self.sources[source] = self.main.sources[source]
            self.processors[source] = Processor(self.sources[source].tee, self.videomixer, self.name + '-' + source, None, self.main)

        self.mixes = {}
        self.buttons = []
        for mix in mixdict['mixes']:
            if type(mix) == dict:
                name, prop = list(mix.items())[0]
            else:
                name, prop = mix, None
            self.mixes[name] = prop
            print('adding mix ', name, prop)

            try: button = Gtk.RadioButton.new_with_label_from_widget(self.buttons[0], name)
            except IndexError: button = Gtk.RadioButton.new_with_label_from_widget(None, name)
            self.box.pack_start(button, False, False, 4)

            button.connect('toggled', self.on_button_toggled, name)
            self.buttons.append(button)

        self.outputs = []
        if mixdict.get('outputs'):
            for output in mixdict['outputs']:
                if type(output) == dict:
                    outputtype, props = list(output.items())[0]
                else:
                    outputtype, props = output, None

                if outputtype == 'simple':
                    output = SimpleVideoSink(self.tee, self.name, None, self.main)
                    self.outputs.append(output)

        self.buttons[0].set_active(True)
        self.on_button_toggled(self.buttons[0], self.buttons[0].get_label())

    def on_button_toggled(self, button, name):
        if button.get_active():
            mix = self.mixes[name]
            print(self.name + ' switching to mix ' + name)

            if not type(mix) == list: mix = []
            for sourcename in self.sources:
                props = {}
                for sourcedict in mix:
                    n, p = list(sourcedict.items())[0]
                    if n == sourcename:
                        props = p
                        break

                processor = self.processors[sourcename]

                processor.alpha.set_property('alpha', props.get('alpha') or 1)

                caps = Gst.Caps.from_string("video/x-raw")
                caps.set_value('width', props.get('width') or int(self.main.settings['resolution'][0]))
                caps.set_value('height', props.get('height') or int(self.main.settings['resolution'][1]))
                processor.capsfilter.set_property('caps', caps)

                processor.sinkpad.set_property('xpos', props.get('x') or 0)
                processor.sinkpad.set_property('ypos', props.get('y') or 0)
                if not props.get('z') == None:
                    processor.sinkpad.set_property('xpos', props.get('z'))



class Main:
    def __init__(self):
        self.settings = yaml.load(open('settings.yaml'))

        self.window = Gtk.Window(title = 'Stir - Video Mixer')
        self.window.connect('destroy', self.quit)
        self.window.maximize()

        self.mixersbox = Gtk.Box()
        self.window.add(self.mixersbox)

        self.pipeline = Gst.Pipeline()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.mixers = {}
        self.sources = {}

        for source in self.settings['sources']:
            name, prop = list(source.items())[0]
            if prop['type'] == 'test':
                self.sources[name] = TestSource(name, prop, self)
            if prop['type'] == 'uri':
                self.sources[name] = URISource(name, prop, self)
            if prop['type'] == 'v4l2':
                self.sources[name] = V4L2Source(name, prop, self)

        for mixer in self.settings['mixers']:
            name, prop = list(mixer.items())[0]
            self.mixers[name] = Mixer(name, prop, self)

        self.window.show_all()

        for mixer in self.mixers.values():
            mixer.previewsink.xid = mixer.previewarea.get_property('window').get_xid()

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, 'pipeline.dot')
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            try:
                msg.src.set_window_handle(msg.src.xid)
            except AttributeError:
                print('not setting xid on sink')
                pass

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())

main = Main()
main.run()
