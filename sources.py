import gi
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11
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

class PulseaudioSource:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.device = props.get('device')
        self.main = main

        self.src = Gst.ElementFactory.make('pulsesrc', 'pulsesrc-' + name)
        self.main.pipeline.add(self.src)
        if self.device: self.src.set_property('device', self.device)
        self.src.set_property('client-name', "Stir - Video Mixer")


class Processor:
    def __init__(self, source, sink, name, props, main):
        self.source = source
        self.sink = sink
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.videoscale = Gst.ElementFactory.make('videoscale', 'scale-' + name)
        self.main.pipeline.add(self.videoscale)
        self.queue.link(self.videoscale)

        caps = Gst.Caps.from_string("video/x-raw")
        caps.set_value('width', int(self.main.settings['resolution'][0]))
        caps.set_value('height', int(self.main.settings['resolution'][1]))
        self.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter-' + name)
        self.main.pipeline.add(self.capsfilter)
        self.capsfilter.set_property('caps', caps)
        self.videoscale.link(self.capsfilter)

        self.rate = Gst.ElementFactory.make('videorate', 'videorate-' + name)
        self.main.pipeline.add(self.rate)
        self.capsfilter.link(self.rate)

        self.alpha = Gst.ElementFactory.make('alpha', 'alpha-' + name)
        self.main.pipeline.add(self.alpha)
        self.rate.link(self.alpha)

        alphapad = self.alpha.get_static_pad('src')
        self.sinkpad = self.sink.get_compatible_pad(alphapad, None)
        alphapad.link(self.sinkpad)