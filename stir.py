#!/usr/bin/python3
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo
GObject.threads_init()
Gst.init(None)

class URISource:
    def __init__(self, uri, main):
        self.uri = uri
        self.main = main

        self.src = Gst.ElementFactory.make('uridecodebin', None)
        self.main.pipeline.add(self.src)
        self.src.set_property('uri', uri)

        self.tee = Gst.ElementFactory.make('uridecodebin', None)
        self.main.pipeline.add(self.tee)

        self.src.connect('pad-added', self.on_pad_added, self.tee)

    def on_pad_added(self, element, srcpad, dest):
        name = srcpad.query_caps(None).to_string()
        print('on_pad_added:', name)
        if name.startswith('video/'):
            sinkpad = dest.get_compatible_pad(srcpad, None)
            srcpad.link(self.sinkpad)

class Processor:
    def __init__(self, source, sink, main):
        self.source = source
        self.sink = sink
        self.main = main

        self.queue = Gst.ElementFactory.make('queue', None)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.rate = Gst.ElementFactory.make('videorate', None)
        self.main.pipeline.add(self.rate)
        self.queue.link(self.rate)

        self.scale = Gst.ElementFactory.make('videoscale', None)
        self.main.pipeline.add(self.scale)
        self.rate.link(self.scale)

        self.alpha = Gst.ElementFactory.make('alpha', None)
        self.main.pipeline.add(self.alpha)
        self.scale.link(self.alpha)

        alphapad = self.alpha.get_static_pad('src')
        self.sinkpad = self.sink.get_compatible_pad(alphapad)
        alphapad.link(self.sinkpad)

class SimpleVideoSink:
    def __init__(self, source, main):
        self.source = source
        self.main = main

        self.autovideosink = Gst.ElementFactory.make('autovideosink', None)
        self.main.pipeline.add(self.autovideosink)
        self.source.link(self.autovideosink)

class Mixer:
    def __init__(self, main, ):
        


class Main:
    def __init__(self):
        self.settings = {'resolution': (1280, 720)}

        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(*self.settings['resolution'])

        self.drawingarea = Gtk.DrawingArea()
        self.window.add(self.drawingarea)

        self.pipeline = Gst.Pipeline()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.mixer = Gst.ElementFactory.make('videomixer', None)
        self.sink = Gst.ElementFactory.make('autovideosink', None)

        self.pipeline.add(self.mixer)
        self.pipeline.add(self.sink)

        self.mixer.link(self.sink)
        self.video = Source('file:///home/hunter/Archives/lappystuff/Videos/Webcam/2010-02-16-115702.ogv', self.pipeline, self.mixer)
        self.video2 = Source('file:///home/hunter/Video/Grad Slideshow/test1.ogv', self.pipeline, self.mixer)

    def run(self):
        self.window.show_all()
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
        self.xid = self.drawingarea.get_property('window').get_xid()
        self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle': msg.src.set_window_handle(self.xid)

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())

main = Main()
main.run()
