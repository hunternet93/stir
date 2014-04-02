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

        self.videorate = Gst.ElementFactory.make('videorate', 'videorate-' + name)
        self.main.pipeline.add(self.videorate)
        self.videorate.set_property('skip-to-first', True)
        self.src.link(self.videorate)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + name)
        self.main.pipeline.add(self.videoconvert)
        self.videorate.link(self.videoconvert)

        self.videoscale = Gst.ElementFactory.make('videoscale', 'videoscale-' + name)
        self.main.pipeline.add(self.videoscale)
        self.videoconvert.link(self.videoscale)

        caps = Gst.Caps.from_string("video/x-raw,format=I420,pixel-aspect-ratio=1/1,framerate="+self.main.settings['framerate'])
        caps.set_value('width', self.main.settings['resolution'][0])
        caps.set_value('height', self.main.settings['resolution'][1])
        self.capsfilter1 = Gst.ElementFactory.make('capsfilter', 'capsfilter1-' + name)
        self.main.pipeline.add(self.capsfilter1)
        self.capsfilter1.set_property('caps', caps)
        self.videoscale.link(self.capsfilter1)

        self.intersink = Gst.ElementFactory.make('intervideosink', 'intervideosink-' + name)
        self.main.pipeline.add(self.intersink)
        self.intersink.set_property('channel', 'intervideo-' + name)
        self.intersink.set_property('async', False)
        self.capsfilter1.link(self.intersink)
        self.intersrc = Gst.ElementFactory.make('intervideosrc', 'intervideosrc-' + name)
        self.main.pipeline.add(self.intersrc)
        self.intersrc.set_property('channel', 'intervideo-' + name)

        self.capsfilter2 = Gst.ElementFactory.make('capsfilter', 'capsfilter2-' + name)
        self.main.pipeline.add(self.capsfilter2)
        self.capsfilter2.set_property('caps', caps)
        self.intersrc.link(self.capsfilter2)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.capsfilter2.link(self.tee)


class DecklinkSource:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.device = props['device']
        self.mode = props['mode']
        self.connection = props['connection']
        self.main = main

        self.src = Gst.ElementFactory.make('decklinksrc', 'decklinksrc-' + name)
        self.main.pipeline.add(self.src)
        self.src.set_property('device-number', self.device)
        self.src.set_property('connection', self.connection)
        self.src.set_property('mode', self.mode)

        self.deinterlace = Gst.ElementFactory.make('deinterlace', 'deinterlace-' + name)
        self.main.pipeline.add(self.deinterlace)
        self.src.link(self.deinterlace)

        self.videorate = Gst.ElementFactory.make('videorate', 'videorate-' + name)
        self.main.pipeline.add(self.videorate)
        self.deinterlace.link(self.videorate)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + name)
        self.main.pipeline.add(self.videoconvert)
        self.videorate.link(self.videoconvert)

        self.videoscale = Gst.ElementFactory.make('videoscale', 'videoscale-' + name)
        self.main.pipeline.add(self.videoscale)
        self.videoconvert.link(self.videoscale)

        caps = Gst.Caps.from_string("video/x-raw,format=I420,pixel-aspect-ratio=1/1,framerate="+self.main.settings['framerate'])
        caps.set_value('width', self.main.settings['resolution'][0])
        caps.set_value('height', self.main.settings['resolution'][1])
        self.capsfilter1 = Gst.ElementFactory.make('capsfilter', 'capsfilter1-' + name)
        self.main.pipeline.add(self.capsfilter1)
        self.capsfilter1.set_property('caps', caps)
        self.videoscale.link(self.capsfilter1)

        self.intersink = Gst.ElementFactory.make('intervideosink', 'intervideosink-' + name)
        self.intersink.set_property('async', False)
        self.main.pipeline.add(self.intersink)
        self.intersink.set_property('channel', 'intervideo-' + name)
        self.capsfilter1.link(self.intersink)
        self.intersrc = Gst.ElementFactory.make('intervideosrc', 'intervideosrc-' + name)
        self.main.pipeline.add(self.intersrc)
        self.intersrc.set_property('channel', 'intervideo-' + name)

        self.capsfilter2 = Gst.ElementFactory.make('capsfilter', 'capsfilter2-' + name)
        self.main.pipeline.add(self.capsfilter2)
        self.capsfilter2.set_property('caps', caps)
        self.intersrc.link(self.capsfilter2)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + name)
        self.main.pipeline.add(self.tee)
        self.capsfilter2.link(self.tee)


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
        self.src.set_property('buffer-time', 10000)


class JackSource:
    def __init__(self, name, props, main):
        self.name = name
        self.props = props
        self.device = props.get('device')
        self.main = main

        self.src = Gst.ElementFactory.make('jackaudiosrc', 'jackaudiosrc-' + name)
        self.main.pipeline.add(self.src)
        self.src.set_property('client-name', "stir")
        self.src.set_property('buffer-time', 10000)


class Processor:
    def __init__(self, source, sink, name, props, main):
        self.source = source
        self.sink = sink
        self.main = main
        self.name = name

        self.videoscale = Gst.ElementFactory.make('videoscale', 'scale-' + name)
        self.main.pipeline.add(self.videoscale)
        self.source.link(self.videoscale)

        caps = Gst.Caps.from_string("video/x-raw, framerate="+self.main.settings['framerate'])
        caps.set_value('width', int(self.main.settings['resolution'][0]))
        caps.set_value('height', int(self.main.settings['resolution'][1]))
        self.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter-' + name)
        self.main.pipeline.add(self.capsfilter)
        self.capsfilter.set_property('caps', caps)
        self.videoscale.link(self.capsfilter)

        self.alpha = Gst.ElementFactory.make('alpha', 'alpha-' + name)
        self.main.pipeline.add(self.alpha)
        self.capsfilter.link(self.alpha)

        alphapad = self.alpha.get_static_pad('src')
        self.sinkpad = self.sink.get_compatible_pad(alphapad, None)
        alphapad.link(self.sinkpad)
