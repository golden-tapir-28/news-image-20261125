#!/usr/bin/env python3
"""THE WORLD -- Wednesday 25 November 2026.

Renders the daily front page (1024x1024 PNG) for the make.fun
news-image-20261125 bounty. All 35 main stories (7 regions x 5) and
11 briefs come from the verified research file for this edition; the
lead story is Putin's retaliation warning as the war spills into the
Baltic.

Rendering: the program builds a self-contained HTML front page and
screenshots it at 1024x1024 with a headless Chromium binary found on
the machine. If no Chromium binary is available it falls back to a
pure-Pillow renderer. Output is deterministic: identical inputs give
an identical PNG.

Usage: python3 main.py [--output PATH]
Environment: MAKEFUN_OUTPUT_DIR (output directory, default ".").
"""

import hashlib
import html
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

DATE_LINE = "Wednesday 25 November 2026"
MASTHEAD = "THE WORLD"

LEAD = (
    "Putin vows \u2018inevitable\u2019 retaliation as Ukraine\u2019s war "
    "spills into the Baltic",
    "President Vladimir Putin warns retaliation is \u201cinevitable\u201d after "
    "Ukraine keeps striking Russian refineries despite President Trump\u2019s "
    "direct request to stop. Moscow accuses Kyiv of \u201cterrorist acts\u201d "
    "after Ukrainian drones hit the cargo ship Sparta II in the Gulf of "
    "Finland and a warship off Benghazi, Libya \u2014 Ukraine confirms it "
    "struck Sparta II on 21 November and calls the Libya strikes lawful "
    "self-defence. A Russian night attack on Zaporizhzhia kills two "
    "civilians and wounds 44, including four children, as the war\u2019s "
    "newest theatres multiply from the Baltic to the Mediterranean.",
    "[25 Nov]",
)

# (region, [(headline, summary, tag), ...]) -- 7 regions x 5 stories.
REGIONS = [
    ("North America", [
        ("Tariff threat rattles markets as US readies trade probe findings",
         "The Trump administration prepares findings of a trade probe into "
         "excess industrial capacity among 16 partners, including China and "
         "the EU, that could bring new tariffs. The Nasdaq falls 1.5% and "
         "the S&P 500 0.5%; in Asia, South Korea\u2019s KOSPI drops 5.3%, "
         "Taiwan 5.1% and Japan\u2019s Nikkei 2.9%. Nvidia gives back 5.9% "
         "after Monday\u2019s surge.", "[25 Nov]"),
        ("CIA and spy chief\u2019s office hit by hack on unclassified systems",
         "The CIA and the Office of the Director of National Intelligence "
         "suffer an apparent hack of unclassified systems used for "
         "open-source intelligence analysis. Officials stress no classified "
         "information was affected; early indications suggest the hack may "
         "have originated in China.", "[25 Nov]"),
        ("Trump says Iran war \u2018funded\u2019 through January",
         "Trump tells the New York Post his war effort with Iran is "
         "\u201cfunded\u201d through the end of January, warning Democrats "
         "taking Congress in January could turn \u201ca total win\u201d into "
         "\u201ca loss\u201d. Israel favours complete regime change; Trump "
         "says the war is already \u201ceffectively over\u201d.",
         "[24 Nov]"),
        ("Trump to meet El-Sayed on \u2018Trumpcare\u2019 pitch",
         "Trump plans to meet Michigan Senator-elect Abdul El-Sayed to "
         "discuss his \u201cMedicare for All\u201d proposal, pitched as "
         "\u201cTrumpcare\u201d. Trump calls the idea \u201cvery smart\u201d "
         "and says he and the new Democratic majorities could do "
         "\u201cgreat things together\u201d.", "[24 Nov]"),
        ("Huawei found guilty on 10 of 12 counts in US trial",
         "A New York jury finds Huawei guilty on 10 of 12 criminal counts, "
         "including bank fraud and conspiracy to steal trade secrets, after "
         "a three-month trial. Huawei rejects the verdicts; the firm has "
         "long been a target of the Trump administration.", "[24 Nov]"),
    ]),
    ("Europe", [
        ("EU unveils 22nd sanctions package against Russia",
         "The European Commission proposes its 22nd sanctions package "
         "against Russia, including a ban on Russian teams competing under "
         "the Russian flag in the EU and a visa ban for Russian "
         "ex-combatants, plus measures against Russian banks and crypto "
         "platforms.", "[25 Nov]"),
        ("Russian drone briefly enters Polish airspace",
         "Poland\u2019s military says a Russian drone briefly entered Polish "
         "airspace during an attack on Ukraine, and authorisation was given "
         "to shoot it down \u2014 but it was not fired on after it changed "
         "course east, \u201ctaking into account the potential threat to "
         "civilians\u201d.", "[24 Nov]"),
        ("European court rules Poland violated Afghan migrant\u2019s rights",
         "The European Court of Human Rights rules Poland violated the "
         "rights of an Afghan migrant at its border with Belarus, in a "
         "judgment handed down in the early hours of Wednesday.",
         "[25 Nov]"),
        ("Commission goes easy on France\u2019s budget",
         "The European Commission\u2019s annual review goes easy on France, "
         "the eurozone\u2019s biggest deficit holder, running a deficit of "
         "5.5% this year. Paris stays under the excessive deficit procedure "
         "but is judged on an acceptable path; Italy may exit it in "
         "spring.", "[24 Nov]"),
        ("EU nature-law talks collapse in Parliament",
         "Centrist coalition talks in the European Parliament break down "
         "over a proposal to reopen the EU\u2019s nature laws. Negotiations "
         "resume on Wednesday ahead of another vote, and the Commission is "
         "due to decide in 2027 whether to reopen the Birds and Habitats "
         "Directives.", "[24 Nov]"),
    ]),
    ("Middle East", [
        ("Iran rules out US talks until seven conditions are met",
         "Iran says it will not negotiate with the US to end the conflict "
         "until seven undisclosed conditions are met. Three oil tankers "
         "struck naval mines and caught fire in the Strait of Hormuz "
         "despite US aerial protection; at least nine Palestinians are "
         "killed in Israeli strikes in Gaza.", "[24 Nov]"),
        ("Hamas security chief killed in Gaza strike",
         "An Israeli drone strike in western Gaza City kills Naim Abu Nahl, "
         "head of Hamas\u2019s internal security service, and wounds four "
         "others. At least seven Palestinians are killed in Gaza on "
         "Tuesday; the overall toll reaches 74,746 since October 2023.",
         "[24 Nov]"),
        ("Iraq orders federal forces to seize Kurdish oilfields",
         "Iraq\u2019s premier Ali al-Zaidi directs federal units to seize "
         "oilfields and crossings in Kurdish-run regions, sharply "
         "escalating Baghdad\u2019s dispute with the Kurdish authorities "
         "over oil.", "[25 Nov]"),
        ("Britain sanctions the Houthis and four top officials",
         "Britain sanctions the Houthis in Yemen and four senior leaders, "
         "accusing them of rights abuses including torture and sexual "
         "violence against detainees, as the Saudi-led coalition and the "
         "Houthis trade strikes across the Red Sea.", "[25 Nov]"),
        ("Iran\u2019s medicine shortage leaves patients hunting for drugs",
         "Iranian pharmacies are shutting and hospital supplies have halted "
         "as a medicine shortage bites, with people cutting doses or buying "
         "from informal markets, as war damage worsens the energy crisis "
         "with winter approaching.", "[25 Nov]"),
    ]),
    ("Asia", [
        ("Indonesia\u2019s vice-president resigns amid political strain",
         "Indonesia\u2019s Vice-President Gibran Rakabuming Raka resigns, "
         "starting a process to choose a replacement as the ruling alliance "
         "between President Prabowo Subianto and ex-president Joko Widodo "
         "\u2014 Gibran\u2019s father \u2014 frays.", "[25 Nov]"),
        ("Shenzhou-24 launches with first Pakistani in orbit",
         "China\u2019s Shenzhou-24 lifts off from Jiuquan carrying commander "
         "Tang Hongbo, flight engineer Wu Yi and Muhammad Zeeshan Ali, a "
         "Pakistan Air Force pilot who becomes the first Pakistani in orbit "
         "and the first foreign astronaut aboard Tiangong station.",
         "[25 Nov]"),
        ("China opens graft probe into Shanghai\u2019s top party leader",
         "China\u2019s anticorruption body opens an investigation into Chen "
         "Jining, the leading Communist Party official in Shanghai and a "
         "Politburo member \u2014 the fourth Politburo member pulled into "
         "such a probe since last year.", "[24 Nov]"),
        ("Xiamen Airlines orders 50 Boeing 737-8s",
         "Xiamen Airlines agrees to acquire 50 Boeing 737-8 jets with a "
         "list value of about $7.4 billion \u2014 Boeing\u2019s first major "
         "Chinese order in nearly ten years.", "[25 Nov]"),
        ("Rescuers search for dozens trapped in Indonesian mine",
         "Rescue teams search for what could be \u201cdozens\u201d of workers "
         "trapped in a mine 100 metres deep in Pongkor, Bogor, West Java, "
         "since Monday, when heavy rains inundated the access. Local media "
         "report 30 trapped; the mine is an unauthorised gold operation.",
         "[25 Nov]"),
    ]),
    ("Africa", [
        ("Around 175 migrants unaccounted for after boat lost from Senegal",
         "Around 175 migrants are unaccounted for after contact was lost "
         "with a Europe-bound boat that left Dakar around 9\u201310 November. "
         "Senegal\u2019s navy rescued 974 migrants on five pirogues on "
         "Monday; more than 8,000 arrived in the Canary Islands in the "
         "first 12 days of November.", "[24 Nov]"),
        ("DR Congo military aircraft missing as rebels claim shootdown",
         "DR Congo says a military aircraft is missing after rebels claim "
         "they shot it down; a South African fighter pilot and a Ugandan "
         "officer are reportedly aboard, the BBC reports.", "[24 Nov]"),
        ("Ethiopia and Eritrea mass troops at Badme",
         "Ethiopia repositions forces from the Ethiopia-Eritrea border "
         "toward Tigray\u2019s city belt and keeps fighting TPLF forces "
         "south of Badme, an Eritrean border town regained on 18 November, "
         "in the latest review of the war.", "[24 Nov]"),
        ("Senegal reinstated as AFCON champions",
         "The Court of Arbitration for Sport overturns a CAF decision "
         "stripping Senegal of the 2025 Africa Cup of Nations title, "
         "confirming Senegal as champions after its 1\u20130 win over "
         "Morocco in Rabat; the forfeit ruling is set aside.", "[24 Nov]"),
        ("WHO evacuates Ebola staff in DR Congo amid fighting",
         "WHO staff are evacuated from a hospital in Akwe, Ituri province, "
         "after sheltering there for three days to escape fierce fighting. "
         "The outbreak \u2014 the worst ever recorded in DR Congo \u2014 has "
         "caused 5,775 deaths among 11,762 cases.", "[24 Nov]"),
    ]),
    ("Latin America", [
        ("Hostages held in Cartagena supermarket after failed cash-truck raid",
         "Armed men seize a supermarket in Cartagena, Colombia, after a "
         "failed attempt to rob an armoured cash truck, holding at least 20 "
         "people hostage after releasing 10 of the 30 seized, as police and "
         "soldiers surround the store. The same day, a car bomb near "
         "government offices in Villavicencio injures 22.", "[24 Nov]"),
        ("Lula signs fiscal package and backs a second spending curb",
         "President Lula signs the fiscal adjustment package into law "
         "without vetoes, capping real spending growth at 2% in containment "
         "years and cutting tax breaks, in a package worth R$45\u201356 "
         "billion in 2027. He then authorises a second package curbing "
         "mandatory spending.", "[24 Nov]"),
        ("Bolsonaro\u2019s doctors treat pneumonia as bowel improves",
         "Doctors treating former president Jair Bolsonaro say his bowel "
         "condition is improving after an endoscopy, ruling out emergency "
         "surgery \u2014 but after a vomiting episode they diagnose "
         "bilateral bronchoaspirative pneumonia and start intravenous "
         "antibiotics. Bolsonaro, 71, remains in intensive care.",
         "[24 Nov]"),
        ("US pauses joint military operations with Ecuador",
         "The Trump administration pauses joint military operations with "
         "Ecuador while Washington investigates a lethal operation carried "
         "out by Ecuadorean forces; joint operations were paused by "
         "mid-October, the New York Times reports.", "[24 Nov]"),
        ("WHO chief visits Cuba as healthcare system deteriorates",
         "WHO chief Tedros Adhanom Ghebreyesus visits Cuba as the "
         "country\u2019s healthcare system deteriorates, pledging millions "
         "to the decayed system.", "[24 Nov]"),
    ]),
    ("Oceania / Pacific", [
        ("Australia and Solomon Islands sign security treaty in blow to China",
         "Australia and the Solomon Islands sign a security pact in "
         "Canberra making Canberra the Pacific nation\u2019s defence partner "
         "of choice and committing the islands to keeping foreign military "
         "bases off their territory, as the Solomons\u2019 security "
         "agreement with Beijing faces phaseout.", "[25 Nov]"),
        ("Australia\u2019s inflation jumps to 4.9%",
         "Australia\u2019s October consumer prices climb 4.9% year on year, "
         "above the 4.7% forecast, as fuel and clothing jump; the trimmed "
         "mean of 3.8% is still well above target and ramps up pressure on "
         "the Reserve Bank, which has raised rates by 125 basis points this "
         "year.", "[25 Nov]"),
        ("Australia apologises to LGBTQ veterans",
         "Defence Minister Richard Marles apologises to LGBTQ+ veterans for "
         "decades of military discrimination, in a national apology "
         "described as a \u201cmilestone\u201d.", "[25 Nov]"),
        ("Fiji\u2019s drought emergency could stretch into 2027",
         "Fijians could face prolonged water shortages into early 2027, "
         "with below-normal rainfall expected to persist beyond the peak of "
         "the current El Ni\u00f1o event, the Pacific Islands News "
         "Association reports.", "[25 Nov]"),
        ("Strong El Ni\u00f1o raises drought risk for Guam and Northern Marianas",
         "Guam and the Northern Mariana Islands face an increased risk of "
         "drought in early 2027 as a potentially historic El Ni\u00f1o "
         "develops, following five consecutive months of below-normal "
         "rainfall.", "[25 Nov]"),
    ]),
]

BRIEFS = [
    ("Microsoft declares an internal \u201cCode Red\u201d after its 12\u201313 Nov "
     "global Microsoft 365 outage, setting a one-hour recovery target for "
     "future incidents. \u2014 Reuters [24 Nov]"),
    ("Vaibhav Sooryavanshi, 15, smashes 204 off 53 balls for India A "
     "against UAE, the fastest List A double century. \u2014 BBC [24 Nov]"),
    ("Defending champion D. Gukesh draws game one of the world chess title "
     "match against Javokhir Sindarov in Geneva. \u2014 The Hindu [25 Nov]"),
    ("GTA 6 draws 39 million PS5 players in four days, Sony\u2019s biggest "
     "launch in 30 years. [25 Nov]"),
    ("Norway will give Ukraine at least $7bn in 2027, with air defence "
     "first, Kyiv\u2019s defence minister says in Oslo. \u2014 Reuters "
     "[24 Nov]"),
    ("Russia\u2019s Duma passes the 2027\u201329 budget; defence spending rises "
     "27% to a record 17.1 trillion roubles, about a third of all spending. "
     "\u2014 Moscow Times [24 Nov]"),
    ("Hungary\u2019s PM P\u00e9ter Magyar meets Zelensky in Uzhhorod, the first "
     "visit by a Hungarian prime minister to Ukraine since 2015. \u2014 "
     "Euronews [24 Nov]"),
    ("Landmine casualties hit a five-year peak at 6,929 in 2025, most in "
     "Southeast Asia; civilians are 84% of victims, half of them children. "
     "\u2014 Landmine Monitor [25 Nov]"),
    ("AIDS deaths fell to 570,000 in 2025, the lowest in 20+ years, but "
     "international HIV funding fell 18% and US funding 26%, UNAIDS warns. "
     "\u2014 UNAIDS [24 Nov]"),
    ("A magnitude 5.6 earthquake struck eastern Nepal\u2019s Koshi province "
     "near the Tibet border on Tuesday. [24 Nov]"),
    ("The death toll from a bus\u2013truck collision in Ras Al Khaimah rose to "
     "13 on Tuesday; 14 others were injured. [24 Nov]"),
]


def _esc(text):
    return html.escape(text)


def build_html(scale=1.0):
    """Build the front-page HTML. ``scale`` shrinks all type to fit."""
    f = lambda base: round(base * scale, 1)
    lead_head, lead_sum, lead_tag = LEAD
    regions_html = []
    for name, stories in REGIONS:
        items = []
        for head, summ, tag in stories:
            items.append(
                '<div class="story"><h3>%s <span class="tag">%s</span></h3>'
                "<p>%s</p></div>" % (_esc(head), _esc(tag), _esc(summ))
            )
        regions_html.append(
            '<div class="region"><h2>%s</h2>%s</div>'
            % (_esc(name), "".join(items))
        )
    briefs_html = "".join(
        '<div class="brief">\u2022 %s</div>' % _esc(b) for b in BRIEFS
    )
    css = (
        "* { margin:0; padding:0; box-sizing:border-box; }\n"
        "html,body { width:1024px; background:#fff; }\n"
        "body { font-family: Arial, Helvetica, sans-serif; color:#111; }\n"
        ".page { width:1024px; padding:%spx %spx %spx; }\n"
        ".mast { text-align:center; }\n"
        ".mast h1 { font-family: Georgia, 'Times New Roman', serif; "
        "font-size:%spx; font-weight:700; letter-spacing:%spx; "
        "line-height:1.04; }\n"
        ".dateline { display:flex; justify-content:space-between; "
        "font-size:%spx; letter-spacing:1px; text-transform:uppercase; "
        "border-top:3px solid #111; border-bottom:1px solid #111; "
        "padding:%spx 2px; margin-top:%spx; }\n"
        ".lead { margin-top:%spx; padding-bottom:%spx; "
        "border-bottom:2px solid #111; }\n"
        ".kicker { font-size:%spx; font-weight:800; letter-spacing:2px; "
        "color:#8b0000; text-transform:uppercase; }\n"
        ".lead h2 { font-family: Georgia, 'Times New Roman', serif; "
        "font-size:%spx; font-weight:700; line-height:1.12; "
        "margin:%spx 0 %spx; }\n"
        ".lead p { font-size:%spx; line-height:1.38; }\n"
        ".body { column-count:3; column-gap:%spx; margin-top:%spx; }\n"
        ".region h2 { font-size:%spx; font-weight:800; "
        "letter-spacing:1.5px; text-transform:uppercase; "
        "border-bottom:2px solid #111; padding-bottom:2px; "
        "margin:%spx 0 %spx; break-after:avoid; }\n"
        ".region:first-child h2 { margin-top:0; }\n"
        ".story { break-inside:avoid; margin-bottom:%spx; }\n"
        ".story h3 { font-size:%spx; font-weight:700; line-height:1.22; "
        "margin-bottom:2px; }\n"
        ".story p { font-size:%spx; line-height:1.32; }\n"
        ".tag { font-weight:700; }\n"
        ".briefs { border:1.5px solid #111; padding:%spx %spx; "
        "margin-top:%spx; break-inside:avoid; }\n"
        ".briefs h2 { font-size:%spx; font-weight:800; "
        "letter-spacing:1.5px; border-bottom:1px solid #111; "
        "padding-bottom:3px; margin-bottom:%spx; }\n"
        ".briefs .cols { column-count:2; column-gap:%spx; }\n"
        ".brief { font-size:%spx; line-height:1.32; "
        "margin-bottom:%spx; break-inside:avoid; }\n"
        ".foot { font-size:%spx; text-align:center; color:#555; "
        "margin-top:%spx; }\n"
    ) % (
        f(18), f(26), f(12),           # .page padding
        f(60), f(8),                   # masthead
        f(11), f(4), f(5),             # dateline
        f(10), f(9),                   # .lead
        f(11),                         # kicker
        f(30), f(5), f(4),             # lead h2
        f(13),                         # lead p
        f(16), f(9),                   # .body
        f(12), f(9), f(5),             # region h2
        f(9),                          # .story margin
        f(12),                         # story h3
        f(10.5),                       # story p
        f(8), f(10), f(9),             # .briefs
        f(12), f(5),                   # briefs h2
        f(16),                         # briefs cols gap
        f(10), f(4),                   # .brief
        f(9.5), f(7),                  # .foot
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>THE WORLD</title><style>%s</style></head><body>"
        '<div class="page">'
        '<div class="mast"><h1>%s</h1>'
        '<div class="dateline"><span>%s</span>'
        "<span>35 stories from 7 regions</span>"
        "<span>Edition No. 329</span></div></div>"
        '<div class="lead"><div class="kicker">Lead story \u2014 '
        "Ukraine war spills into the Baltic</div>"
        "<h2>%s</h2><p>%s <span class='tag'>%s</span></p></div>"
        '<div class="body">%s</div>'
        '<div class="briefs"><h2>In brief</h2>'
        '<div class="cols">%s</div></div>'
        '<div class="foot">THE WORLD \u2022 Wednesday 25 November 2026 '
        "\u2022 All stories verified 25 November 2026</div>"
        "</div>"
        "<script>document.title='H:'+document.documentElement.scrollHeight;"
        "</script></body></html>"
        % (
            css, MASTHEAD, DATE_LINE,
            _esc(lead_head), _esc(lead_sum), _esc(lead_tag),
            "".join(regions_html), briefs_html,
        )
    )


def _chromium_candidates():
    home = Path.home()
    cands = [
        home / ".cache/ms-playwright/chromium-1193/chrome-linux/chrome",
        home / ".cache/ms-playwright/chromium_headless_shell-1193"
        / "chrome-linux/headless_shell",
    ]
    for name in ("chromium", "chromium-browser", "google-chrome",
                 "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            cands.append(Path(found))
    return [c for c in cands if c.is_file() and os.access(c, os.X_OK)]


def _chromium_args(binary, mode, html_path, png_path=None):
    args = [str(binary)]
    if "headless_shell" not in binary.name:
        args.append("--headless=new")
    args += ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
    if mode == "dom":
        args.append("--dump-dom")
    else:
        args += [
            "--screenshot=" + str(png_path),
            "--window-size=1024,1024",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
        ]
    args.append("file://" + str(html_path))
    return args


def _run(args, timeout=120):
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except (subprocess.TimeoutExpired, OSError):
        return -1, "", ""


def measure_height(binary, html_path):
    """Return the rendered page height in px, or None on failure."""
    code, out, _ = _run(_chromium_args(binary, "dom", html_path))
    if code != 0:
        return None
    m = re.search(r"<title>H:(\d+)</title>", out)
    return int(m.group(1)) if m else None


def render_chromium(binary, html_path, png_path):
    """Screenshot the HTML at 1024x1024; True on success."""
    code, _, _ = _run(_chromium_args(binary, "shot", html_path, png_path))
    return code == 0 and Path(png_path).is_file()


def render_pil(png_path, scale=1.0):
    """Fallback renderer using Pillow only (no browser needed)."""
    from PIL import Image, ImageDraw, ImageFont

    def font(name, size):
        path = Path("/usr/share/fonts/truetype/dejavu") / name
        try:
            return ImageFont.truetype(str(path), int(round(size)))
        except OSError:
            return ImageFont.load_default()

    f = lambda base: base * scale
    W, H = 1024, 1024
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    serif_b = lambda s: font("DejaVuSerif-Bold.ttf", s)
    sans = lambda s: font("DejaVuSans.ttf", s)
    sans_b = lambda s: font("DejaVuSans-Bold.ttf", s)
    margin = 26
    y = 18

    def wrap(text, fnt, width):
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if d.textlength(trial, font=fnt) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def text_block(lines, fnt, x, y0, leading):
        for line in lines:
            d.text((x, y0), line, font=fnt, fill="black")
            y0 += leading
        return y0

    # Masthead.
    title = MASTHEAD
    tf = serif_b(f(58))
    d.text(((W - d.textlength(title, font=tf)) / 2, y), title,
           font=tf, fill="black")
    y += int(f(66))
    d.line([(margin, y), (W - margin, y)], fill="black", width=3)
    y += 5
    d.line([(margin, y), (W - margin, y)], fill="black", width=1)
    y += 6
    df = sans_b(f(11))
    d.text((margin, y), DATE_LINE.upper(), font=df, fill="black")
    right = "35 STORIES FROM 7 REGIONS"
    d.text((W - margin - d.textlength(right, font=df), y), right,
           font=df, fill="black")
    y += int(f(24))
    d.line([(margin, y), (W - margin, y)], fill="black", width=1)
    y += int(f(10))

    # Lead story.
    lead_head, lead_sum, lead_tag = LEAD
    d.text((margin, y), "LEAD STORY \u2014 UKRAINE WAR SPILLS INTO "
           "THE BALTIC", font=sans_b(f(11)), fill="#8b0000")
    y += int(f(16))
    lh = serif_b(f(28))
    y = text_block(wrap(lead_head, lh, W - 2 * margin), lh, margin, y,
                   int(f(33)))
    y += 3
    lp = sans(f(13))
    y = text_block(wrap(lead_sum + " " + lead_tag, lp, W - 2 * margin),
                   lp, margin, y, int(f(17)))
    y += int(f(8))
    d.line([(margin, y), (W - margin, y)], fill="black", width=2)
    y += int(f(10))

    # Body: three columns, stories assigned greedily by height.
    col_w = (W - 2 * margin - 2 * 16) // 3
    col_x = [margin, margin + col_w + 16, margin + 2 * (col_w + 16)]
    hf = sans_b(f(12))
    shf = sans_b(f(11.5))
    spf = sans(f(10.5))
    blocks = []
    for name, stories in REGIONS:
        blocks.append(("head", name, None))
        for head, summ, tag in stories:
            blocks.append(("story", head, summ + " " + tag))
    col_h = [0, 0, 0]
    col_items = [[], [], []]
    for kind, a, b in blocks:
        if kind == "head":
            h = int(f(26))
        else:
            h = (len(wrap(a, shf, col_w)) * int(f(14))
                 + len(wrap(b, spf, col_w)) * int(f(13)) + int(f(9)))
        col = min(range(3), key=lambda i: col_h[i])
        col_items[col].append((kind, a, b))
        col_h[col] += h
    body_top = y
    for ci in range(3):
        yy = body_top
        for kind, a, b in col_items[ci]:
            if kind == "head":
                d.text((col_x[ci], yy), a.upper(), font=hf, fill="black")
                yy += int(f(18))
                d.line([(col_x[ci], yy), (col_x[ci] + col_w, yy)],
                       fill="black", width=2)
                yy += int(f(8))
            else:
                yy = text_block(wrap(a, shf, col_w), shf, col_x[ci], yy,
                                int(f(14)))
                yy = text_block(wrap(b, spf, col_w), spf, col_x[ci], yy,
                                int(f(13)))
                yy += int(f(9))
    y = body_top + max(col_h) + int(f(10))
    if y > H - 230:
        # Body ran too tall to fit the briefs box; let the caller retry
        # at a smaller scale instead of drawing a broken page.
        return False

    # Briefs box.
    d.rectangle([(margin, y), (W - margin, H - 26)], outline="black",
                width=2)
    y += int(f(8))
    d.text((margin + 10, y), "IN BRIEF", font=sans_b(f(12)), fill="black")
    y += int(f(20))
    d.line([(margin + 10, y), (W - margin - 10, y)], fill="black",
           width=1)
    y += int(f(6))
    bf = sans(f(10))
    bw = (W - 2 * margin - 20 - 16) // 2
    bx = [margin + 10, margin + 10 + bw + 16]
    half = (len(BRIEFS) + 1) // 2
    for ci, group in enumerate((BRIEFS[:half], BRIEFS[half:])):
        yy = y
        for b in group:
            yy = text_block(wrap("\u2022 " + b, bf, bw), bf, bx[ci], yy,
                            int(f(13)))
            yy += int(f(4))
    img.save(str(png_path), "PNG")
    return True


def png_size(path):
    """Return (width, height) of a PNG file using only the stdlib."""
    with open(path, "rb") as fh:
        head = fh.read(33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out_path = None
    if "--output" in argv:
        out_path = Path(argv[argv.index("--output") + 1])
    if out_path is None:
        out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "."))
        out_path = out_dir / "entry.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    forced = os.environ.get("NEWSIMAGE_RENDERER", "").lower()
    binaries = _chromium_candidates() if forced != "pil" else []
    method = None
    if binaries:
        binary = binaries[0]
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "front.html"
            chosen = None
            # Fine steps so the page fills the 1024px height instead of
            # leaving a large empty band at the bottom.
            for i in range(21):
                scale = round(1.0 - 0.02 * i, 2)
                html_path.write_text(build_html(scale), encoding="utf-8")
                height = measure_height(binary, html_path)
                if height is None:
                    break
                if height <= 1020:
                    chosen = scale
                    break
            if chosen is None:
                html_path.write_text(build_html(0.6), encoding="utf-8")
                chosen = 0.6
            if render_chromium(binary, html_path, out_path):
                method = "chromium (scale %.2f)" % chosen
    if method is None:
        for scale in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
            try:
                ok = render_pil(out_path, scale)
            except Exception:
                ok = False
            if ok:
                # PIL path always draws inside 1024x1024 by construction.
                method = "pillow (scale %.2f)" % scale
                break
    if method is None:
        print("error: could not render entry.png", file=sys.stderr)
        return 1
    size = png_size(out_path)
    if size != (1024, 1024):
        print("error: entry.png is %s, expected 1024x1024" % (size,),
              file=sys.stderr)
        return 1
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print("rendered %s (%s)" % (out_path, method))
    print("size: %d bytes, dimensions: %sx%s, sha256: %s"
          % (out_path.stat().st_size, size[0], size[1], digest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
