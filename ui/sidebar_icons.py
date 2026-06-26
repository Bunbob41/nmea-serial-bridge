"""Iconly sidebar icons — sourced from Iconly V3.0 Free (Figma community file).

SVG path data is copied verbatim from the downloaded Figma SVG exports.
`make_sidebar_icon_multistate(key)` returns a two-state PySide6 QIcon.

Icon → sidebar mapping
-----------------------
  swap     → Control   (bidirectional serial bridge)
  send     → Fleet     (network streaming / fan-out)
  scan     → Hub       (connection discovery / scan)
  setting  → Theme     (application settings)
  activity → Activity  (live NMEA data stream)
  work     → Presets   (saved configurations)
"""
from __future__ import annotations

# ── Clean SVG bodies (24×24, fill inherited from root, background stripped) ──
# Each string is a complete <svg> element ready to render.

_SVG_DATA: dict[str, str] = {
    "swap": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M16.8396 5.79639C17.2193 5.79639 17.5331 6.07854 17.5828 6.44462L17.5896 6.54639V20.1642C17.5896 20.5784 17.2538 20.9142 16.8396 20.9142C16.4599 20.9142 16.1461 20.632 16.0964 20.2659L16.0896 20.1642V6.54639C16.0896 6.13217 16.4254 5.79639 16.8396 5.79639Z"/>'
        '<path d="M20.3857 15.5389C20.6779 15.2453 21.1528 15.2442 21.4464 15.5364C21.7133 15.8021 21.7384 16.2187 21.5213 16.5128L21.4488 16.5971L17.3711 20.6938C17.1045 20.9615 16.6863 20.9859 16.3922 20.7668L16.3079 20.6938L12.2302 16.5971C11.9379 16.3035 11.939 15.8287 12.2326 15.5364C12.4995 15.2708 12.9162 15.2475 13.2093 15.4661L13.2933 15.5389L16.8391 19.1009L20.3857 15.5389Z"/>'
        '<path d="M6.91113 3.08289C7.29083 3.08289 7.60462 3.36504 7.65429 3.73112L7.66113 3.83289V17.4507C7.66113 17.8649 7.32535 18.2007 6.91113 18.2007C6.53144 18.2007 6.21764 17.9185 6.16798 17.5524L6.16113 17.4507V3.83289C6.16113 3.41867 6.49692 3.08289 6.91113 3.08289Z"/>'
        '<path d="M6.37972 3.30317C6.64624 3.03542 7.06449 3.01108 7.3586 3.23015L7.44283 3.30317L11.5206 7.39984C11.8128 7.69341 11.8117 8.16828 11.5182 8.4605C11.2513 8.72615 10.8346 8.74939 10.5414 8.53086L10.4575 8.45805L6.91105 4.89494L3.36505 8.45805C3.0994 8.72493 2.68279 8.7501 2.38868 8.53292L2.30439 8.4605C2.03751 8.19485 2.01234 7.77824 2.22952 7.48412L2.30194 7.39984L6.37972 3.30317Z"/>'
        '</svg>'
    ),
    "send": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M10.8049 14.8178L14.4619 20.7508C14.6219 21.0108 14.8719 21.0078 14.9729 20.9938C15.0739 20.9798 15.3169 20.9178 15.4049 20.6228L19.9779 5.17777C20.0579 4.90477 19.9109 4.71877 19.8449 4.65277C19.7809 4.58677 19.5979 4.44577 19.3329 4.52077L3.87695 9.04677C3.58394 9.13277 3.51994 9.37877 3.50594 9.47977C3.49194 9.58277 3.48794 9.83777 3.74695 10.0008L9.74794 13.7538L15.0499 8.39577C15.3409 8.10177 15.8159 8.09877 16.1109 8.38977C16.4059 8.68077 16.4079 9.15677 16.1169 9.45077L10.8049 14.8178ZM14.8949 22.4998C14.1989 22.4998 13.5609 22.1458 13.1849 21.5378L9.30794 15.2468L2.95194 11.2718C2.26694 10.8428 1.90894 10.0788 2.01994 9.27577C2.12994 8.47277 2.68094 7.83477 3.45494 7.60777L18.9109 3.08177C19.6219 2.87377 20.3839 3.07077 20.9079 3.59277C21.4319 4.11977 21.6269 4.88977 21.4149 5.60377L16.8419 21.0478C16.6129 21.8248 15.9729 22.3738 15.1719 22.4808C15.0779 22.4928 14.9869 22.4998 14.8949 22.4998Z"/>'
        '</svg>'
    ),
    "scan": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M22.75 13.955H1.75C1.336 13.955 1 13.619 1 13.205C1 12.791 1.336 12.455 1.75 12.455H22.75C23.164 12.455 23.5 12.791 23.5 13.205C23.5 13.619 23.164 13.955 22.75 13.955Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M20.8799 9.745C20.4659 9.745 20.1299 9.409 20.1299 8.995V7.481C20.1299 5.838 18.7919 4.5 17.1469 4.5H15.9419C15.5279 4.5 15.1919 4.164 15.1919 3.75C15.1919 3.336 15.5279 3 15.9419 3H17.1469C19.6189 3 21.6299 5.011 21.6299 7.481V8.995C21.6299 9.409 21.2939 9.745 20.8799 9.745Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M3.62012 9.745C3.20612 9.745 2.87012 9.409 2.87012 8.995V7.481C2.87012 5.011 4.88112 3 7.35312 3H8.58912C9.00312 3 9.33912 3.336 9.33912 3.75C9.33912 4.164 9.00312 4.5 8.58912 4.5H7.35312C5.70812 4.5 4.37012 5.838 4.37012 7.481V8.995C4.37012 9.409 4.03412 9.745 3.62012 9.745Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M17.1469 21.7606H15.9419C15.5279 21.7606 15.1919 21.4246 15.1919 21.0106C15.1919 20.5966 15.5279 20.2606 15.9419 20.2606H17.1469C18.7919 20.2606 20.1299 18.9226 20.1299 17.2786V13.2036C20.1299 12.7896 20.4659 12.4536 20.8799 12.4536C21.2939 12.4536 21.6299 12.7896 21.6299 13.2036V17.2786C21.6299 19.7496 19.6189 21.7606 17.1469 21.7606Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M8.58887 21.7606H7.35287C4.88087 21.7606 2.86987 19.7496 2.86987 17.2786V13.2036C2.86987 12.7896 3.20587 12.4536 3.61987 12.4536C4.03387 12.4536 4.36987 12.7896 4.36987 13.2036V17.2786C4.36987 18.9226 5.70787 20.2606 7.35287 20.2606H8.58887C9.00287 20.2606 9.33887 20.5966 9.33887 21.0106C9.33887 21.4246 9.00287 21.7606 8.58887 21.7606Z"/>'
        '</svg>'
    ),
    "setting": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M7.20232 17.4405C7.43132 17.4405 7.66032 17.4695 7.88432 17.5295C8.56032 17.7115 9.14732 18.1635 9.49532 18.7705C9.72132 19.1515 9.84632 19.5965 9.85032 20.0505C9.85032 20.7005 10.3723 21.2215 11.0143 21.2215H12.2673C12.9063 21.2215 13.4283 20.7035 13.4313 20.0645C13.4273 19.3585 13.7033 18.6875 14.2083 18.1825C14.7063 17.6845 15.4023 17.3855 16.0983 17.4055C16.5543 17.4165 16.9933 17.5395 17.3803 17.7595C17.9373 18.0785 18.6483 17.8885 18.9703 17.3385L19.6343 16.2315C19.7823 15.9765 19.8253 15.6565 19.7463 15.3615C19.6683 15.0665 19.4723 14.8105 19.2083 14.6595C18.5903 14.3035 18.1493 13.7295 17.9663 13.0415C17.7853 12.3665 17.8843 11.6295 18.2373 11.0225C18.4673 10.6225 18.8043 10.2855 19.2083 10.0535C19.7503 9.73649 19.9403 9.02749 19.6253 8.47549C19.6123 8.45349 19.6003 8.43049 19.5903 8.40649L19.0043 7.39049C18.6853 6.83549 17.9753 6.64449 17.4183 6.96149C16.8163 7.31749 16.1003 7.41949 15.4123 7.23849C14.7253 7.06049 14.1493 6.62549 13.7903 6.01149C13.5603 5.62749 13.4353 5.18049 13.4313 4.72549C13.4403 4.38349 13.3203 4.07649 13.1023 3.85149C12.8853 3.62749 12.5803 3.50049 12.2673 3.50049H11.0143C10.7043 3.50049 10.4143 3.62149 10.1953 3.83949C9.97732 4.05849 9.85832 4.34949 9.86032 4.65949C9.83932 6.12149 8.64432 7.29849 7.19732 7.29849C6.73332 7.29349 6.28632 7.16849 5.89832 6.93649C5.35332 6.62649 4.64132 6.81749 4.32232 7.37249L3.64532 8.48549C3.33532 9.02349 3.52532 9.73449 4.07732 10.0555C4.89632 10.5295 5.40732 11.4135 5.40732 12.3615C5.40732 13.3095 4.89632 14.1925 4.07532 14.6675C3.52632 14.9855 3.33632 15.6925 3.65432 16.2425L4.28532 17.3305C4.44132 17.6115 4.69632 17.8145 4.99132 17.8975C5.28532 17.9795 5.60932 17.9445 5.87932 17.7945C6.27632 17.5615 6.73832 17.4405 7.20232 17.4405ZM12.2673 22.7215H11.0143C9.54532 22.7215 8.35032 21.5275 8.35032 20.0585C8.34832 19.8775 8.29632 19.6895 8.19932 19.5265C8.04232 19.2525 7.78832 19.0565 7.49532 18.9785C7.20432 18.9005 6.88532 18.9435 6.62332 19.0955C5.99532 19.4455 5.25632 19.5305 4.58032 19.3405C3.90532 19.1495 3.32232 18.6855 2.98032 18.0705L2.35532 16.9935C1.62432 15.7255 2.05932 14.1005 3.32532 13.3685C3.68432 13.1615 3.90732 12.7755 3.90732 12.3615C3.90732 11.9475 3.68432 11.5605 3.32532 11.3535C2.05832 10.6175 1.62432 8.98849 2.35432 7.72049L3.03232 6.60749C3.75332 5.35349 5.38332 4.91149 6.65432 5.64149C6.82732 5.74449 7.01532 5.79649 7.20632 5.79849C7.82932 5.79849 8.35032 5.28449 8.36032 4.65249C8.35632 3.95549 8.63132 3.28649 9.13232 2.78149C9.63532 2.27749 10.3033 2.00049 11.0143 2.00049H12.2673C12.9833 2.00049 13.6793 2.29449 14.1783 2.80549C14.6763 3.31949 14.9513 4.02449 14.9303 4.73949C14.9323 4.90049 14.9853 5.08649 15.0813 5.24949C15.2403 5.51949 15.4913 5.70949 15.7893 5.78749C16.0873 5.86149 16.3993 5.82149 16.6643 5.66449C17.9443 4.93349 19.5733 5.37149 20.3043 6.64149L20.9273 7.72049C20.9433 7.74949 20.9573 7.77749 20.9693 7.80649C21.6313 9.05749 21.1893 10.6325 19.9593 11.3515C19.7803 11.4545 19.6353 11.5985 19.5353 11.7725C19.3803 12.0415 19.3373 12.3615 19.4153 12.6555C19.4953 12.9555 19.6863 13.2045 19.9553 13.3585C20.5623 13.7075 21.0153 14.2955 21.1963 14.9745C21.3773 15.6525 21.2783 16.3885 20.9253 16.9955L20.2613 18.1015C19.5303 19.3575 17.9013 19.7925 16.6343 19.0605C16.4653 18.9635 16.2703 18.9105 16.0763 18.9055H16.0703C15.7813 18.9055 15.4843 19.0285 15.2683 19.2435C15.0493 19.4625 14.9293 19.7545 14.9313 20.0645C14.9243 21.5335 13.7293 22.7215 12.2673 22.7215Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M11.645 10.4746C10.605 10.4746 9.75903 11.3216 9.75903 12.3616C9.75903 13.4016 10.605 14.2466 11.645 14.2466C12.685 14.2466 13.531 13.4016 13.531 12.3616C13.531 11.3216 12.685 10.4746 11.645 10.4746ZM11.645 15.7466C9.77803 15.7466 8.25903 14.2286 8.25903 12.3616C8.25903 10.4946 9.77803 8.97461 11.645 8.97461C13.512 8.97461 15.031 10.4946 15.031 12.3616C15.031 14.2286 13.512 15.7466 11.645 15.7466Z"/>'
        '</svg>'
    ),
    "activity": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M7.21629 16.0029C7.05629 16.0029 6.89529 15.9519 6.75929 15.8479C6.43129 15.5949 6.36929 15.1239 6.62229 14.7959L9.61529 10.9059C9.73729 10.7469 9.91829 10.6439 10.1163 10.6189C10.3183 10.5929 10.5163 10.6489 10.6733 10.7739L13.4933 12.9889L15.9603 9.80587C16.2143 9.47687 16.6843 9.41587 17.0123 9.67187C17.3403 9.92587 17.4003 10.3969 17.1463 10.7239L14.2163 14.5039C14.0943 14.6619 13.9143 14.7649 13.7163 14.7889C13.5163 14.8159 13.3183 14.7579 13.1603 14.6349L10.3423 12.4209L7.81129 15.7099C7.66329 15.9019 7.44129 16.0029 7.21629 16.0029Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M19.9674 3.5C19.3214 3.5 18.7954 4.025 18.7954 4.672C18.7954 5.318 19.3214 5.845 19.9674 5.845C20.6134 5.845 21.1394 5.318 21.1394 4.672C21.1394 4.025 20.6134 3.5 19.9674 3.5ZM19.9674 7.345C18.4944 7.345 17.2954 6.146 17.2954 4.672C17.2954 3.198 18.4944 2 19.9674 2C21.4414 2 22.6394 3.198 22.6394 4.672C22.6394 6.146 21.4414 7.345 19.9674 7.345Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M16.233 22.7032H7.629C4.262 22.7032 2 20.3382 2 16.8182V8.73616C2 5.21116 4.262 2.84216 7.629 2.84216H14.897C15.311 2.84216 15.647 3.17816 15.647 3.59216C15.647 4.00616 15.311 4.34216 14.897 4.34216H7.629C5.121 4.34216 3.5 6.06616 3.5 8.73616V16.8182C3.5 19.5232 5.082 21.2032 7.629 21.2032H16.233C18.741 21.2032 20.362 19.4822 20.362 16.8182V9.77916C20.362 9.36516 20.698 9.02916 21.112 9.02916C21.526 9.02916 21.862 9.36516 21.862 9.77916V16.8182C21.862 20.3382 19.6 22.7032 16.233 22.7032Z"/>'
        '</svg>'
    ),
    "work": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M11.9951 17.4268C11.5811 17.4268 11.2451 17.0908 11.2451 16.6768V14.1398C11.2451 13.7258 11.5811 13.3898 11.9951 13.3898C12.4091 13.3898 12.7451 13.7258 12.7451 14.1398V16.6768C12.7451 17.0908 12.4091 17.4268 11.9951 17.4268Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M3.50024 11.3931C5.87624 12.6841 8.87224 13.3911 11.9902 13.3911C15.1142 13.3911 18.1132 12.6841 20.4902 11.3931V8.39108C20.4902 7.11608 19.4592 6.08008 18.1902 6.08008H5.81024C4.53624 6.08008 3.50024 7.11208 3.50024 8.38108V11.3931ZM11.9902 14.8911C8.44524 14.8911 5.02824 14.0331 2.37124 12.4771C2.14124 12.3431 2.00024 12.0971 2.00024 11.8301V8.38108C2.00024 6.28508 3.70924 4.58008 5.81024 4.58008H18.1902C20.2862 4.58008 21.9902 6.28908 21.9902 8.39108V11.8301C21.9902 12.0971 21.8482 12.3431 21.6192 12.4771C18.9622 14.0331 15.5422 14.8911 11.9902 14.8911Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M15.4951 6.07612C15.0811 6.07612 14.7451 5.74012 14.7451 5.32612V4.96012C14.7451 4.15512 14.0901 3.50012 13.2851 3.50012H10.7051C9.90012 3.50012 9.24512 4.15512 9.24512 4.96012V5.32612C9.24512 5.74012 8.90912 6.07612 8.49512 6.07612C8.08112 6.07612 7.74512 5.74012 7.74512 5.32612V4.96012C7.74512 3.32812 9.07312 2.00012 10.7051 2.00012H13.2851C14.9171 2.00012 16.2451 3.32812 16.2451 4.96012V5.32612C16.2451 5.74012 15.9091 6.07612 15.4951 6.07612Z"/>'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M17.7949 21.7402H6.19494C4.11994 21.7402 2.37294 20.1192 2.21594 18.0492L2.02594 15.5402C1.99494 15.1272 2.30494 14.7662 2.71794 14.7352C3.13294 14.7202 3.49094 15.0132 3.52294 15.4272L3.71194 17.9352C3.80994 19.2272 4.89994 20.2402 6.19494 20.2402H17.7949C19.0899 20.2402 20.1809 19.2272 20.2779 17.9352L20.4679 15.4272C20.4999 15.0132 20.8669 14.7192 21.2729 14.7352C21.6859 14.7662 21.9949 15.1272 21.9639 15.5402L21.7739 18.0492C21.6169 20.1192 19.8699 21.7402 17.7949 21.7402Z"/>'
        '</svg>'
    ),

    # ── Placeholder icons for remaining sidebar sections ────────────────────
    # Simple geometric filled shapes that clearly communicate each function.

    # NMEA: funnel / filter (data mode selection = filtering)
    "funnel": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M3 5H21V8L14 15V21H10V15L3 8V5Z"/>'
        '</svg>'
    ),

    # Black-box / session recording: floppy disk (label area + shutter as cutouts)
    "floppy": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="'
        'M3 4C3 3.448 3.448 3 4 3H20C20.552 3 21 3.448 21 4V20C21 20.552 20.552 21 20 21H4C3.448 21 3 20.552 3 20V4Z '
        'M5 4H17V11H5Z '
        'M8 14H16V20H8Z'
        '"/>'
        '</svg>'
    ),

    # File log: document outline with content lines (evenodd cutout)
    "document": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="'
        'M6 3C5.448 3 5 3.448 5 4V20C5 20.552 5.448 21 6 21H18C18.552 21 19 20.552 19 20V8L15 3H6Z '
        'M8 11H16V13H8Z '
        'M8 15H16V17H8Z '
        'M8 18H13V20H8Z'
        '"/>'
        '</svg>'
    ),

    # Dashboard (phone): monitor screen + stand + base (web interface)
    "monitor": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path fill-rule="evenodd" clip-rule="evenodd" d="'
        'M3 4C2.448 4 2 4.448 2 5V16C2 16.552 2.448 17 3 17H21C21.552 17 22 16.552 22 16V5C22 4.448 21.552 4 21 4H3Z '
        'M4 6H20V15H4V6Z'
        '"/>'
        '<path d="M10 17H14V20H10V17Z"/>'
        '<path d="M7 20H17V22H7V20Z"/>'
        '</svg>'
    ),

    # Presets: bookmark ribbon (saved configurations)
    "bookmark": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M5 3H19C19.552 3 20 3.448 20 4V20L12 16L4 20V4C4 3.448 4.448 3 5 3Z"/>'
        '</svg>'
    ),

    # Inject: lightning bolt (fast inject / trigger)
    "bolt": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M13 2L5 14H11L10 22L19 10H13Z"/>'
        '</svg>'
    ),

    # Terminal: > _ prompt symbols
    "prompt": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M3 8L9 12L3 16L5 16L11 12L5 8Z"/>'
        '<path d="M12 16H20V18H12V16Z"/>'
        '</svg>'
    ),

    # Checks / automated tests: bold checkmark
    "check": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="FILL">'
        '<path d="M3 13L9 19L18 3L21 3L9 22L0 13Z"/>'
        '</svg>'
    ),

    # Survey map: globe with meridians (tactical chart view)
    "globe": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="FILL" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/>'
        '<ellipse cx="12" cy="12" rx="4" ry="9"/>'
        '<path d="M3 12H21"/>'
        '<path d="M4.5 7.5H19.5"/>'
        '<path d="M4.5 16.5H19.5"/>'
        '</svg>'
    ),
}

# ── Icon-to-sidebar-section mapping ──────────────────────────────────────────
SIDEBAR_ICON_MAP: dict[str, str] = {
    # Control group
    "control":   "swap",
    "activity":  "activity",
    # Setup group
    "presets":   "bookmark",
    "hub":       "scan",
    "fleet":     "send",
    "nmea":      "funnel",
    # Logging group
    "black_box": "floppy",
    "file_log":  "document",
    # Bench Tools group
    "phone":     "monitor",
    "inject":    "bolt",
    "terminal":  "prompt",
    "checks":    "check",
    "theme":     "setting",
    "survey_map": "globe",
}


def _render_svg(key: str, color: str) -> "QtGui.QPixmap | None":
    """Render the named SVG in *color* and return a 20×20 QPixmap."""
    try:
        from PySide6 import QtCore, QtGui, QtSvg
    except ImportError:
        return None
    template = _SVG_DATA.get(key)
    if not template:
        return None
    svg_bytes = template.replace("FILL", color).encode("utf-8")
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg_bytes))
    if not renderer.isValid():
        return None
    size = 20
    pm = QtGui.QPixmap(size, size)
    pm.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


def hub_card_icon_pixmap(
    kind: str,
    *,
    color: str = "#8b9cb8",
    size: int = 22,
) -> "QtGui.QPixmap | None":
    """Iconly pixmap for Connection Hub endpoint cards (serial vs network)."""
    key = "send" if kind == "network" else "swap"
    pm = _render_svg(key, color)
    if pm is None:
        return None
    if pm.width() == size and pm.height() == size:
        return pm
    try:
        from PySide6 import QtCore, QtGui
    except ImportError:
        return pm
    return pm.scaled(
        size,
        size,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )


def make_sidebar_icon_multistate(
    key: str,
    *,
    normal_color: str = "#8888aa",
    active_color: str = "#ddd0ee",
) -> "QtGui.QIcon | None":
    """Return a two-state QIcon: dim when unchecked, bright when checked/active."""
    pm_normal = _render_svg(key, normal_color)
    if pm_normal is None:
        return None
    pm_active = _render_svg(key, active_color)
    try:
        from PySide6 import QtGui
    except ImportError:
        return None
    icon = QtGui.QIcon()
    icon.addPixmap(pm_normal, QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    if pm_active:
        icon.addPixmap(pm_active, QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        icon.addPixmap(pm_active, QtGui.QIcon.Mode.Active, QtGui.QIcon.State.Off)
    return icon


def make_sidebar_icon(key: str, color: str = "#8888aa") -> "QtGui.QIcon | None":
    """Single-state QIcon helper."""
    pm = _render_svg(key, color)
    if pm is None:
        return None
    try:
        from PySide6 import QtGui
        return QtGui.QIcon(pm)
    except ImportError:
        return None


def make_sidebar_pixmaps(
    key: str,
    *,
    normal_color: str = "#8888aa",
    active_color: str = "#ddd0ee",
) -> "tuple[QtGui.QPixmap, QtGui.QPixmap] | None":
    """Return (pm_normal, pm_active) pixmaps for use with _SvgNavButton.

    Returns None if the SVG key is unknown or rendering fails.
    """
    pm_normal = _render_svg(key, normal_color)
    if pm_normal is None:
        return None
    pm_active = _render_svg(key, active_color)
    if pm_active is None:
        pm_active = pm_normal
    return pm_normal, pm_active
