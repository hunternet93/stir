import gi
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11, Gdk

class H264Encoder:
    def __init__(self, source, name, props, main):
        self.source, self.name, self.main = source, name, main
        self.queue = Gst.ElementFactory.make('queue', 'queue-' + self.name)
        self.queue.set_property('max-size-time', 2000000)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + self.name)
        self.main.pipeline.add(self.videoconvert)
        self.queue.link(self.videoconvert)
        # Caps to fix OMXPlayer decoding, OMX doesn't support Y444 format
        caps = Gst.Caps.from_string("video/x-raw,format=I420")
        self.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter-' + self.name)
        self.main.pipeline.add(self.capsfilter)
        self.capsfilter.set_property('caps', caps)
        self.videoconvert.link(self.capsfilter)

        self.encoder = Gst.ElementFactory.make('x264enc', 'x264enc-' + self.name)
        self.main.pipeline.add(self.encoder)
        self.encoder.set_property('tune', props.get('tune') or 'zerolatency')
        self.encoder.set_property('speed-preset', props.get('preset') or 'fast')
        self.encoder.set_property('bitrate', props.get('bitrate') or 2048)
        if props.get('qp'): self.encoder.set_property('quantizer', props['qp'])
        if props.get('keyint'): self.encoder.set_property('key-int-max', props['keyint'])
        self.capsfilter.link(self.encoder)

        self.h264parse = Gst.ElementFactory.make('h264parse', 'h264parse-' + self.name)
        self.main.pipeline.add(self.h264parse)
        self.encoder.link(self.h264parse)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + self.name)
        self.main.pipeline.add(self.tee)
        self.h264parse.link(self.tee)

        self.fakequeue = Gst.ElementFactory.make('queue', 'fakequeue-' + self.name)
        self.main.pipeline.add(self.fakequeue)
        self.tee.link(self.fakequeue)

        self.fakesink = Gst.ElementFactory.make('fakesink', 'fakesink-' + self.name)
        self.main.pipeline.add(self.fakesink)
        self.fakequeue.link(self.fakesink)


class AACEncoder:
    def __init__(self, source, name, props, main):
        self.source, self.name, self.main = source, name, main
        self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
        self.main.pipeline.add(self.audioconvert)
        self.main.audiotee.link(self.audioconvert)

        self.encoder = Gst.ElementFactory.make('faac', 'faac-' + self.name)
        self.main.pipeline.add(self.encoder)
        self.audioconvert.link(self.encoder)

        self.aacparse = Gst.ElementFactory.make('aacparse', 'aacparse-' + self.name)
        self.main.pipeline.add(self.aacparse)
        self.encoder.link(self.aacparse)

        self.tee = Gst.ElementFactory.make('tee', 'tee-' + self.name)
        self.main.pipeline.add(self.tee)
        self.aacparse.link(self.tee)

        self.fakequeue = Gst.ElementFactory.make('queue', 'fakequeue-' + self.name)
        self.main.pipeline.add(self.fakequeue)
        self.tee.link(self.fakequeue)

        self.fakesink = Gst.ElementFactory.make('fakesink', 'fakesink-' + self.name)
        self.main.pipeline.add(self.fakesink)
        self.fakequeue.link(self.fakesink)
