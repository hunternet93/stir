#!/usr/bin/python3
import yaml, gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11
from sources import *
from sinks import *
from encoders import *

GObject.threads_init()
Gst.init(None)
Gtk.init(None)

class Mixer:
    def __init__(self, name, mixdict, main):
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
        self.videomixer.set_property('background', 1)
        self.main.pipeline.add(self.videomixer)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.videomixer.link(self.tee)

        self.previewqueue = Gst.ElementFactory.make('queue', 'previewqueue-' + name)
        self.previewqueue.set_property('max-size-time', 100000)
        self.main.pipeline.add(self.previewqueue)
        self.tee.link(self.previewqueue)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + name)
        self.main.pipeline.add(self.videoconvert)
        self.previewqueue.link(self.videoconvert)

        self.previewsink = Gst.ElementFactory.make('xvimagesink', 'previewsink-' + name)
        self.previewsink.set_property('sync', False)
        self.previewsink.set_property('async', False)
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
                name, props = list(mix.items())[0]
            else:
                name, props = mix, None
            self.mixes[name] = props

            for prop in props:
                if not prop.get('key') == None:
                    key = str(prop['key'])
                    label = '(' + key + ') ' + name
                    break
                else:
                    key = None
                    label = name
                    break

            try: button = Gtk.RadioButton.new_with_label_from_widget(self.buttons[0], label)
            except IndexError: button = Gtk.RadioButton.new_with_label_from_widget(None, label)
            self.box.pack_start(button, False, False, 4)

            button.sname = name
            button.connect('toggled', self.on_button_toggled, name)
            if key:
                kv = getattr(Gdk, 'KEY_' + key)
                button.add_accelerator('activate', self.main.accel, kv, Gdk.ModifierType(0), Gtk.AccelFlags(1))

            self.buttons.append(button)

        self.encoders = {}
        if mixdict.get('encoders'):
            for encoder in mixdict['encoders']:
                name, props = list(encoder.items())[0]
                if props['type'] == 'h264':
                    self.encoders[name] = H264Encoder(self.tee, self.name + '-encoder-' + name, props, self.main)
                if props['type'] == 'aac':
                    self.encoders[name] = AACEncoder(self.main.audiotee, self.name + '-encoder-' + name, props, self.main)

        self.outputs = []
        if mixdict.get('outputs'):
            for output in mixdict['outputs']:
                if type(output) == dict:
                    outputtype, props = list(output.items())[0]
                else:
                    outputtype, props = output, None

                if outputtype == 'simple':
                    output = SimpleVideoSink(self.tee, self.name + str(len(self.outputs)), props, self.main)
                    self.outputs.append(output)
                if outputtype == 'fullscreen':
                    output = FullscreenVideoSink(self.tee, self.name + str(len(self.outputs)), props, self.main)
                    self.outputs.append(output)
                if outputtype == 'tsudp':
                    output = TSUDPSink(self.encoders, self.name + str(len(self.outputs)), props, self.main)
                    self.outputs.append(output)
                if outputtype == 'tsrecord':
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                    self.box.pack_start(box, False, False, 4)
                    self.box.reorder_child(box, 1)
                    self.outputs.append(TSRecord(self.encoders, self.name + str(len(self.outputs)), props, self.main, box))

        self.buttons[0].set_active(True)
        self.on_button_toggled(self.buttons[0], self.buttons[0].sname)

    def on_button_toggled(self, button, name):
        if button.get_active():
            mix = self.mixes[name]

            if not type(mix) == list: mix = []
            for sourcename in self.sources:
                if sourcename == 'key': continue
                props = {}
                for sourcedict in mix:
                    n, p = list(sourcedict.items())[0]
                    if n == sourcename:
                        props = p
                        break

                processor = self.processors[sourcename]

                if not props.get('alpha') == None: processor.alpha.set_property('alpha', props.get('alpha'))
                else: processor.alpha.set_property('alpha', 1)

                if not props.get('chroma') == None:
                    processor.alpha.set_property('method', 3)
                    processor.alpha.set_property('target-r', props.get('chroma')[0])
                    processor.alpha.set_property('target-g', props.get('chroma')[1])
                    processor.alpha.set_property('target-b', props.get('chroma')[2])
                else:
                    processor.alpha.set_property('method', 0)
                if not props.get('chroma-noise') == None:
                    processor.alpha.set_property('noise-level', props.get('chroma-noise'))
                else:
                    processor.alpha.set_property('noise-level', 2)
                if not props.get('chroma-black-sensitivity') == None:
                    processor.alpha.set_property('black-sensitivity', props.get('chroma-black-sensitivity'))
                else:
                    processor.alpha.set_property('black-sensitivity', 100)
                if not props.get('chroma-white-sensitivity') == None:
                    processor.alpha.set_property('white-sensitivity', props.get('chroma-white-sensitivity'))
                else:
                    processor.alpha.set_property('white-sensitivity', 100)
                if not props.get('angle') == None:
                    processor.alpha.set_property('angle', props.get('angle'))
                else:
                    processor.alpha.set_property('angle', 20)

                caps = Gst.Caps.from_string("video/x-raw,framerate="+self.main.settings['framerate'])
                caps.set_value('width', props.get('width') or int(self.main.settings['resolution'][0]))
                caps.set_value('height', props.get('height') or int(self.main.settings['resolution'][1]))
                processor.capsfilter.set_property('caps', caps)

                processor.sinkpad.set_property('xpos', props.get('x') or 0)
                processor.sinkpad.set_property('ypos', props.get('y') or 0)
                if not props.get('z') == None:
                    processor.sinkpad.set_property('zorder', props.get('z'))


class Main:
    def __init__(self):
        self.settings = yaml.load(open('settings.yaml'))

        self.window = Gtk.Window(title = 'Stir - Video Mixer')
        self.window.connect('destroy', self.quit)
        self.window.maximize()

        self.accel = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel)

        self.mixersbox = Gtk.Box(homogeneous = True)
        self.window.add(self.mixersbox)

        self.pipeline = Gst.Pipeline()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.audiomixer = Gst.ElementFactory.make('adder', 'audiomixer')
        self.pipeline.add(self.audiomixer)

        self.audiotee = Gst.ElementFactory.make('tee', 'tee-audio')
        self.pipeline.add(self.audiotee)
        self.audiomixer.link(self.audiotee)

        self.mixers = {}
        self.sources = {}
        self.audiosources = {}
        self.audiosinks = {}

        for source in self.settings['sources']:
            name, prop = list(source.items())[0]
            if prop['type'] == 'test':
                self.sources[name] = TestSource(name, prop, self)
            elif prop['type'] == 'uri':
                self.sources[name] = URISource(name, prop, self)
            elif prop['type'] == 'v4l2':
                self.sources[name] = V4L2Source(name, prop, self)
            elif prop['type'] == 'decklink':
                self.sources[name] = DecklinkSource(name, prop, self)

            elif prop['type'] == 'pulse':
                self.audiosources[name] = PulseaudioSource(name, prop, self)
            elif prop['type'] == 'alsa':
                self.audiosources[name] = ALSASource(name, prop, self)
            elif prop['type'] == 'jack':
                self.audiosources[name] = JackSource(name, prop, self)

        for mixer in self.settings['mixers']:
            name, prop = list(mixer.items())[0]
            if name == 'audio':
                for output in prop['outputs']:
                    if type(output) == dict: n, p = list(output.items())[0]
                    else: n, p = output, None
                    if n == 'udp':
                        self.audiosinks[name] = UDPSink(self.audiotee, 'audio-'+n, p, self)
                    elif n == 'simple':
                        self.audiosinks[name] = SimpleAudioSink(self.audiotee, 'audio-'+n, p, self)

            else:
                self.mixers[name] = Mixer(name, prop, self)

        if len(self.audiosources) < 1:
            self.audiomixer.unlink(self.audiotee)
            self.pipeline.remove(self.audiomixer)
            self.pipeline.remove(self.audiotee)
            del self.audiomixer, self.audiotee

        for source in self.audiosources.values():
            source.src.link(self.audiomixer)

        self.window.show_all()

        for mixer in self.mixers.values():
            mixer.previewsink.xid = mixer.previewarea.get_property('window').get_xid()

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, 'pipeline')
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            try:
                msg.src.set_window_handle(msg.src.xid)
            except AttributeError:
                pass

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())

main = Main()
main.run()
