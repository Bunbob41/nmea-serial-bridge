"""One-shot patch: replace guide HTML strings in tool_tabs.py."""
NEW_UDP = '_GUIDE_UDP = """\n' + """<h2>UDP \u2014 listen vs remote</h2>
<p><em><b>UDP listen</b> (default): this PC receives datagrams on a bound port \u2014 typical for
Trimble/INS Ethernet NMEA. <b>UDP remote</b> (Advanced): send to one fixed host:port.</em></p>
<hr/>
<h3>UDP listen (most survey installs)</h3>
<ol>
  <li><b>Control tab \u2192 Serial link:</b> set <b>COM</b> + <b>Baud</b> (e.g. COM7 @ 115200).</li>
  <li><b>Control tab \u2192 Network path:</b> set <b>Listen host</b> (e.g. <code>0.0.0.0</code>)
      and <b>Listen port</b> (e.g. <code>10110</code>).
      These are the <em>receive</em> fields \u2014 not target/destination.</li>
  <li>Optional: <b>Fan-out \u2014 send serial data to all UDP peers</b> \u2014 COM\u2192network is copied to
      every sender that has talked to this port (UDP listen only).</li>
  <li>Press <b>\u25b6 Start.</b> The header banner should turn green.
      Check the <b>Telemetry</b> tab \u2014 the Network chip confirms the listen socket is open.</li>
  <li>To reuse later: Settings \u2192 Presets \u2192 <b>Save as\u2026</b> (load when stopped).</li>
</ol>
<h3>UDP remote (fixed peer \u2014 bench or one chart PC)</h3>
<ol>
  <li>Control tab \u2192 Network path \u2192 check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>UDP remote.</b></li>
  <li><b>UDP remote (fixed peer)</b> \u2192 <b>Host</b> (e.g. <code>127.0.0.1</code> for local software)
      and <b>Port</b> (e.g. <code>10110</code>).</li>
  <li>Press <b>\u25b6 Start.</b> Fan-out does not apply in remote mode.</li>
</ol>
<p class="note">Advanced network is also accessible from Settings \u2192 Presets if you prefer to
configure there, then press \u25b6 Start in the header.</p>
""" + '"""'

NEW_TCP_CLIENT = '_GUIDE_TCP_CLIENT = """\n' + """<h2>TCP client \u2014 connect outward to a server</h2>
<p><em>Use when your serial device should join an existing TCP service (remote host listens;
this app connects as the client).</em></p>
<hr/>
<h3>Steps</h3>
<ol>
  <li><b>Control tab \u2192 Serial link:</b> correct <b>COM</b> and <b>Baud.</b></li>
  <li>Control tab \u2192 Network path \u2192 check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>TCP client.</b></li>
  <li><b>TCP client</b> group \u2192 <b>Host</b> (server IP) and <b>Port.</b></li>
  <li>Optional: <b>TCP reconnect delay</b> (seconds between retries if the server drops).</li>
  <li>Press <b>\u25b6 Start</b> \u2014 the app actively opens the TCP connection.
      Watch the Network chip in the Telemetry tab for confirmation.</li>
  <li>Save the setup: Settings \u2192 Presets \u2192 <b>Save as\u2026</b> when it works.</li>
</ol>
<p class="note">TCP client requires Advanced network to be checked in Control \u2192 Network path.</p>
""" + '"""'

NEW_TCP_SERVER = '_GUIDE_TCP_SERVER = """\n' + """<h2>TCP server \u2014 host a port on this PC</h2>
<p><em>Use when Hypack, a chart plotter, or another machine must connect <em>to</em> this PC
to read/write the COM port.</em></p>
<hr/>
<h3>Steps</h3>
<ol>
  <li><b>Control tab \u2192 Serial link:</b> set <b>COM</b> + <b>Baud.</b></li>
  <li>Control tab \u2192 Network path \u2192 check <b>Advanced network (TCP / UDP remote / all modes).</b></li>
  <li>Under <b>Mode</b>, select <b>TCP server.</b></li>
  <li><b>TCP server</b> group \u2192 <b>Bind</b>
      (<code>0.0.0.0</code> = any interface, <code>127.0.0.1</code> = this PC only)
      and <b>Port</b> (e.g. <code>4001</code>). Add an inbound Windows Firewall rule for
      the port if external clients need access.</li>
  <li>Press <b>\u25b6 Start</b> \u2014 the app listens until a client connects (one client at a time).
      The header status banner updates when a client attaches.</li>
  <li>Point your client software at this PC's IP and the chosen listen port.</li>
</ol>
<p class="note">Bench TCP test: Settings \u2192 Diagnostics \u2192 automated TCP stress/demo buttons
(require TCP server mode + bridge running).</p>
""" + '"""'

NEW_CHECKLIST = '_GUIDE_CHECKLIST = """\n' + """<h2>Before you press \u25b6 Start</h2>
<p><em>Quick checks when nothing moves on the wire or sentences look wrong.</em></p>
<hr/>
<ul>
  <li><b>COM:</b> correct port (hit Refresh), not held by PuTTY/Tera Term/another app \u2014
      use <b>Unlock COM</b> in the Hub tab if shown. Baud matches the receiver exactly.</li>
  <li><b>UDP listen:</b> Listen host / Listen port in the Control tab match how the
      sender is configured; ping the INS from Settings \u2192 Terminal if needed.</li>
  <li><b>UDP remote / TCP:</b> Advanced network checked in Control \u2192 Network path;
      correct mode radio selected; host/port fields match the peer.</li>
  <li><b>Ports:</b> integers <code>1</code>\u201365535; avoid &lt; <code>1024</code>
      unless the OS permits it. No two apps can bind the same port simultaneously.</li>
  <li><b>Firewall:</b> add an inbound rule for UDP listen / TCP server ports if other
      machines need to reach this PC.</li>
  <li><b>NMEA mode</b> (Settings \u2192 NMEA):
      <b>Passthrough</b> for normal GNSS receivers;
      <b>Strict + sentence filter</b> to drop malformed lines;
      <b>Raw binary</b> only for RTCM or non-NMEA byte streams.</li>
  <li><b>While running:</b> the header status banner turns green; the <b>Telemetry</b>
      tab shows Serial and Network chips with live Hz and byte counts.
      Drops and rejects are called out in plain language.</li>
</ul>
<p class="note">Still stuck? Open <b>Getting started\u2026</b> above or run
Settings \u2192 Diagnostics \u2192 <b>Bench checklist</b> with the bridge stopped.</p>
""" + '"""'


def replace_block(text: str, var_name: str, replacement: str) -> str:
    marker = f'{var_name} = """'
    s = text.find(marker)
    if s < 0:
        print(f"NOT FOUND: {var_name}")
        return text
    # Find the closing triple-quote after the opening one
    e = text.find('\n"""', s + len(marker))
    if e < 0:
        print(f"CLOSING TRIPLE-QUOTE NOT FOUND for {var_name}")
        return text
    e += len('\n"""')
    return text[:s] + replacement + text[e:]


path = "ui/tool_tabs.py"
content = open(path, encoding="utf-8").read()
content = replace_block(content, "_GUIDE_UDP", NEW_UDP)
content = replace_block(content, "_GUIDE_TCP_CLIENT", NEW_TCP_CLIENT)
content = replace_block(content, "_GUIDE_TCP_SERVER", NEW_TCP_SERVER)
content = replace_block(content, "_GUIDE_CHECKLIST", NEW_CHECKLIST)
open(path, "w", encoding="utf-8").write(content)
print("Done — guide strings replaced.")
