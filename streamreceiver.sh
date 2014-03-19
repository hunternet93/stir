#/usr/bin/env bash
gst-launch-1.0 udpsrc address=224.1.2.3 port=5555 caps="application/x-rtp, media=(str)video, encoding-name=(str)H264, clock-rate=(int)90000" ! rtph264depay ! decodebin ! videoconvert ! autovideosink sync=false \
udpsrc address=224.1.2.3 port=5556 caps="application/x-rtp, media=(str)audio, encoding-name=(str)L16, clock-rate=(int)48000, channels=(int)2, payload=(int)96" ! rtpL16depay ! audioconvert ! pulsesink buffer-time=10000
