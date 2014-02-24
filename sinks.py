import gi
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11

class SimpleVideoSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + self.name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.autovideosink = Gst.ElementFactory.make('autovideosink', 'autovideosink' + self.name)
        self.main.pipeline.add(self.autovideosink)
        self.queue.link(self.autovideosink)

class UDPSink:
    def __init__(self, source, name, props, main):
        # TODO: Eventually add support for different encoders/muxers
        self.source = source
        self.name = name
        self.main = main

        self.videoqueue = Gst.ElementFactory.make('queue', 'videoqueue-' + self.name)
        self.main.pipeline.add(self.videoqueue)
        self.source.link(self.videoqueue)

        self.x264enc = Gst.ElementFactory.make('x264enc', 'x264enc-' + self.name)
        self.main.pipeline.add(self.x264enc)
        self.x264enc.set_propert('tune', 'zerolatency')
        self.videoqueue.link(self.x264enc)

        self.muxer = Gst.ElementFactory.make('mpegtsmux', 'muxer-' + self.name)
        self.main.pipeline.add(self.muxer)
        self.x264enc.link(self.muxer)

        self.udpsink = Gst.ElementFactory.make('udpsink', 'udpsink-' + self.name)
        self.main.pipeline.add(self.udpsink)
        self.udpsink.set_property('host', props['host'])
        self.udpsink.set_property('port', props.get('port') or 6473)
        self.muxer.link(self.udpsink)

        if props.get('audio'): # Finish!
            self.audioqueue = Gst.ElementFactory.make('queue', 'audioqueue-' + self.name)
            self.main.pipeline.add(self.audioqueue)
            self.main.audiotee.link(self.audioqueue)

            self.faac = Gst.ElementFactory.make('voaacenc', 'faac-' + self.name)
            self.main.pipeline.add(self.faac)
            self.audioqueue.link(self.faac)

            self.faac.link(self.muxer)
