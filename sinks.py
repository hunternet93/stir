import gi
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11, Gdk

class SimpleVideoSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.autovideosink = Gst.ElementFactory.make('autovideosink', 'autovideosink-simple-' + self.name)
        self.autovideosink.set_property('sync', False)
        self.main.pipeline.add(self.autovideosink)
        self.source.link(self.autovideosink)


class FullscreenVideoSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.window = Gtk.Window(title="Stir - " + self.name + " Output")
        self.drawingarea = Gtk.DrawingArea()
        self.window.add(self.drawingarea)

        screen = Gdk.Display.get_default().get_screen(0)
        self.window.set_screen(screen)
        rect = screen.get_monitor_geometry(props['screen'])
        self.window.move(rect.x, rect.y)

        self.window.fullscreen()
        self.window.set_keep_above(True)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-' + self.name)
        self.main.pipeline.add(self.videoconvert)
        self.source.link(self.videoconvert)

        self.videosink = Gst.ElementFactory.make('xvimagesink', 'xvimagesink-fullscreen-' + self.name)
        self.videosink.set_property('sync', False)
        self.main.pipeline.add(self.videosink)
        self.videoconvert.link(self.videosink)

        self.window.show_all()
        self.videosink.xid = self.drawingarea.get_property('window').get_xid()


class SimpleAudioSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
        self.main.pipeline.add(self.audioconvert)
        self.source.link(self.audioconvert)

        self.autoaudiosink = Gst.ElementFactory.make('pulsesink', 'pulsesink-' + self.name)
        self.main.pipeline.add(self.autoaudiosink)
        self.autoaudiosink.set_property('buffer-time', 10000)
        self.audioconvert.link(self.autoaudiosink)


class TSUDPSink:
    def __init__(self, source, name, props, main):
        # TODO: Eventually add support for different encoders/muxers
        self.source = source
        self.name = name
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', 'queue-' + self.name)
        self.queue.set_property('max-size-time', 10000)
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
        self.encoder.set_property('tune', 'zerolatency')
        self.encoder.set_property('speed-preset', props.get('preset') or 'fast')
        self.encoder.set_property('bitrate', props.get('bitrate') or 2048)
        self.capsfilter.link(self.encoder)

        self.muxer = Gst.ElementFactory.make('mpegtsmux', 'mpegtsmux-' + self.name)
        self.main.pipeline.add(self.muxer)
        self.encoder.link(self.muxer)

        if props.get('audio'):
            self.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert-' + self.name)
            self.main.pipeline.add(self.audioconvert)
            self.main.audiotee.link(self.audioconvert)

            self.faac = Gst.ElementFactory.make('faac', 'faac-' + self.name)
            self.main.pipeline.add(self.faac)
            self.audioconvert.link(self.faac)

            self.faac.link(self.muxer)

        self.udpsink = Gst.ElementFactory.make('udpsink', 'udpsink-' + self.name)
        self.main.pipeline.add(self.udpsink)
        self.udpsink.set_property('host', props['host'])
        self.udpsink.set_property('port', props.get('port') or 6473)
        if props.get('iface'): self.udpsink.set_property('multicast-iface', props['iface'])
        self.udpsink.set_property('sync', False)
        self.muxer.link(self.udpsink)
