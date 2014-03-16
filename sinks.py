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

        self.autovideosink = Gst.ElementFactory.make('autovideosink', 'autovideosink-' + self.name)
        self.autovideosink.set_property('sync', False)
        self.main.pipeline.add(self.autovideosink)
        self.queue.link(self.autovideosink)


class SimpleAudioSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + self.name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
        self.main.pipeline.add(self.audioconvert)
        self.queue.link(self.audioconvert)

        self.autoaudiosink = Gst.ElementFactory.make('pulsesink', 'pulsesink-' + self.name)
        self.main.pipeline.add(self.autoaudiosink)
        self.autoaudiosink.set_property('buffer-time', 10000)
        self.audioconvert.link(self.autoaudiosink)


class UDPSink:
    def __init__(self, source, name, props, main):
        # TODO: Eventually add support for different encoders/muxers
        self.source = source
        self.name = name
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + self.name)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        if props['encoder'] == 'h264':
            self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + self.name)
            self.main.pipeline.add(self.videoconvert)
            self.queue.link(self.videoconvert)

            self.encoder = Gst.ElementFactory.make('x264enc', 'x264enc-' + self.name)
            self.main.pipeline.add(self.encoder)
            self.encoder.set_property('tune', 'zerolatency')
            self.encoder.set_property('speed-preset', props.get('preset') or 'fast')
            self.videoconvert.link(self.encoder)

            self.rtppay = Gst.ElementFactory.make('rtph264pay', 'rtph264pay-' + self.name)
            self.main.pipeline.add(self.rtppay)
            self.encoder.link(self.rtppay)
        elif props['encoder'] == 'aac':
            self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
            self.main.pipeline.add(self.audioconvert)
            self.queue.link(self.audioconvert)

            self.encoder = Gst.ElementFactory.make('voaacenc', 'voaacenc-' + self.name)
            self.main.pipeline.add(self.encoder)
            self.audioconvert.link(self.encoder)

            self.rtppay = Gst.ElementFactory.make('rtpmp4apay', 'rtpmp4apay-' + self.name)
            self.main.pipeline.add(self.rtppay)
            self.encoder.link(self.rtppay)
        elif props['encoder'] == 'l16':
            self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
            self.main.pipeline.add(self.audioconvert)
            self.queue.link(self.audioconvert)

            self.rtppay = Gst.ElementFactory.make('rtpL16pay', 'rtpL16pay-' + self.name)
            self.main.pipeline.add(self.rtppay)
            self.audioconvert.link(self.rtppay)

        self.udpsink = Gst.ElementFactory.make('udpsink', 'udpsink-' + self.name)
        self.main.pipeline.add(self.udpsink)
        self.udpsink.set_property('host', props['host'])
        self.udpsink.set_property('port', props.get('port') or 6473)
        self.udpsink.set_property('sync', False)
        self.rtppay.link(self.udpsink)
