import time, gi
from gi.repository import GObject, Gst, Gtk, GstVideo, GdkX11, Gdk

class SimpleVideoSink:
    def __init__(self, source, name, props, main):
        self.source = source
        self.name = name
        self.main = main

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-simple-' + self.name)
        self.main.pipeline.add(self.videoconvert)
        self.source.link(self.videoconvert)

        self.autovideosink = Gst.ElementFactory.make('autovideosink', 'autovideosink-simple-' + self.name)
        self.autovideosink.set_property('sync', False)
        self.main.pipeline.add(self.autovideosink)
        self.videoconvert.link(self.autovideosink)


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
        self.window.set_accept_focus(False)
        self.window.set_skip_pager_hint(True)
        self.window.set_skip_taskbar_hint(True)

        self.queue = Gst.ElementFactory.make('queue', 'queue-fullscreen-' + self.name)
        self.queue.set_property('max-size-time', 10000)
        self.main.pipeline.add(self.queue)
        self.source.link(self.queue)

        self.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert-fullscreen-' + self.name)
        self.main.pipeline.add(self.videoconvert)
        self.queue.link(self.videoconvert)

        self.videosink = Gst.ElementFactory.make('xvimagesink', 'xvimagesink-fullscreen-' + self.name)
        self.videosink.set_property('sync', False)
        self.videosink.set_property('async', False)
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
    def __init__(self, encoders, name, props, main):
        # TODO: Eventually add support for different encoders/muxers
        self.encoders = encoders
        self.name = name
        self.main = main

        self.muxer = Gst.ElementFactory.make('mpegtsmux', 'mpegtsmux-' + self.name)
        self.main.pipeline.add(self.muxer)

        self.udpsink = Gst.ElementFactory.make('udpsink', 'udpsink-' + self.name)
        self.main.pipeline.add(self.udpsink)
        self.udpsink.set_property('host', props['host'])
        self.udpsink.set_property('port', props.get('port') or 6473)
        if props.get('iface'): self.udpsink.set_property('multicast-iface', props['iface'])
        self.udpsink.set_property('sync', False)
        self.muxer.link(self.udpsink)

        for encoder in props.get('encoders'):
            print('tsudp linking to', encoder)
            encoders[encoder].tee.link(self.muxer)


class TSFileSink:
    def __init__(self, encoders, name, props, main):
        self.name, self.main = name, main
        self.queues = []

        self.muxer = Gst.ElementFactory.make('mpegtsmux', 'mpegtsmux-' + self.name)
        self.main.pipeline.add(self.muxer)

        self.filesink = Gst.ElementFactory.make('filesink', 'filesink-' + self.name)
        self.main.pipeline.add(self.filesink)
        self.filesink.set_property('location', props['directory'] + '/Stir - ' + time.strftime('%Y-%m-%d %I:%M:%S %p') + '.ts')
        self.filesink.set_property('sync', False)
        self.filesink.set_property('async', False)
        self.muxer.link(self.filesink)

        self.encoders = []
        for encoder in props.get('encoders'): self.encoders.append(encoders[encoder])
        for encoder in self.encoders:
            queue = Gst.ElementFactory.make('queue', 'queue' + str(len(self.queues)) + '-' + self.name)
            self.main.pipeline.add(queue)
            queue.link(self.muxer)
            self.queues.append(queue)
            encoder.tee.link(queue)

        print(self.main.pipeline.get_state(5))

    def stop(self):
        self.muxer.get_static_pad('sink').send_event(Gst.Event.new_eos())
        for queue in self.queues:
            queue.set_state(Gst.State.NULL)
            queue.unlink(self.muxer)
            self.main.pipeline.remove(queue)

        self.muxer.set_state(Gst.State.NULL)
        self.muxer.unlink(self.filesink)
        self.main.pipeline.remove(self.muxer)

        self.filesink.set_state(Gst.State.NULL)
        self.main.pipeline.remove(self.filesink)

class TSRecord:
    def __init__(self, encoders, name, props, main, box):
        self.encoders, self.name, self.props, self.main, self.box = encoders, name, props, main, box
        self.button = Gtk.ToggleButton.new_with_label('Record')
        self.button.connect('toggled', self.on_button_toggled)
        self.box.pack_start(self.button, False, False, 4)
        self.label = Gtk.Label()
        self.label.set_markup("<b>Not Recording</b>")
        self.box.pack_start(self.label, False, False, 4)

        self.tsfilesink = None

    def on_button_toggled(self, button):
        print('onbuttontoggled')
        if button.get_active():
            self.tsfilesink = TSFileSink(self.encoders, self.name, self.props, self.main)
            self.button.set_label('Stop')
            self.label.set_markup("Recording to " + self.tsfilesink.filesink.get_property('location'))

        else:
            self.tsfilesink.stop()
            self.tsfilesink = None
            self.button.set_label('Record')
            self.label.set_markup("<b>Not Recording</b>")
