"""Build the six-page submission report from checked-in verification evidence.

Requires reportlab (available in the Codex bundled Python runtime). The demo
does not need this dependency. Run from any directory with Python -B.
"""
from pathlib import Path
import hashlib
import json

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Frame, Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/phase1_technical_report.pdf"
EVIDENCE = ROOT / "audit/phase1"
NAVY = colors.HexColor("#152C43")
TEAL = colors.HexColor("#087F8C")
INK = colors.HexColor("#243447")
MUTED = colors.HexColor("#526574")
PALE = colors.HexColor("#EDF5F7")
W, H = A4
MARGIN = 43
WIDTH = W - 2 * MARGIN

FONT, BOLD = "Helvetica", "Helvetica-Bold"
if Path("C:/Windows/Fonts/arial.ttf").exists():
    pdfmetrics.registerFont(TTFont("ReportArial", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("ReportArialBold", "C:/Windows/Fonts/arialbd.ttf"))
    pdfmetrics.registerFontFamily("ReportArial", normal="ReportArial", bold="ReportArialBold")
    FONT, BOLD = "ReportArial", "ReportArialBold"

BODY = ParagraphStyle("body", fontName=FONT, fontSize=10.1, leading=14.1, textColor=INK, spaceAfter=8)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.9, leading=12, spaceAfter=5)
CELL = ParagraphStyle("cell", parent=SMALL, fontSize=9, leading=11.7, spaceAfter=0)
HEAD = ParagraphStyle("head", fontName=BOLD, fontSize=12, leading=16, textColor=TEAL, spaceBefore=8, spaceAfter=6)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.1, leading=11, textColor=NAVY, spaceAfter=8, backColor=PALE, borderPadding=7)


def p(text, style=BODY):
    return Paragraph(text, style)


def h(text):
    return p(text, HEAD)


def table(rows, widths):
    white = ParagraphStyle("white", parent=CELL, textColor=colors.white, fontName=BOLD)
    values = [[p(str(v), white if i == 0 else CELL) for v in row] for i,row in enumerate(rows)]
    t = Table(values, colWidths=widths, hAlign="LEFT")
    t.spaceAfter = 8
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALE, colors.white]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#CDDFE3")),
    ]))
    return t


class Diagram(Flowable):
    def __init__(self, kind):
        Flowable.__init__(self)
        self.kind = kind
        self.width = WIDTH
        self.height = {"architecture": 213, "packet": 92, "recovery": 123}[kind]

    def draw(self):
        c = self.canv
        def box(x, y, width, title, sub, zone=""):
            c.setFillColor(PALE); c.setStrokeColor(TEAL)
            c.roundRect(x, y, width, 49, 5, fill=1, stroke=1)
            c.setFillColor(NAVY); c.setFont(BOLD, 9)
            c.drawCentredString(x + width/2, y+31, title)
            c.setFont(FONT, 8.5)
            c.drawCentredString(x + width/2, y+15, sub)
            if zone:
                c.setFont(FONT, 8); c.setFillColor(MUTED)
                c.drawCentredString(x + width/2, y-12, zone)
        def arrow(x1, y1, x2, y2, label="", label_y=None):
            import math
            c.setStrokeColor(TEAL); c.setLineWidth(1.2)
            c.line(x1, y1, x2, y2)
            a = math.atan2(y2-y1, x2-x1)
            for off in (-0.5, 0.5):
                c.line(x2, y2, x2-6*math.cos(a+off), y2-6*math.sin(a+off))
            if label:
                c.setFont(FONT, 8); c.setFillColor(MUTED)
                c.drawCentredString((x1+x2)/2, label_y if label_y is not None else (y1+y2)/2+7, label)
        if self.kind == "architecture":
            c.setFillColor(TEAL); c.setFont(BOLD, 10)
            c.drawString(0, 198, "1  SAVE A FINDING AND SEND IT OUTSIDE")
            xs = [0, 134, 268, 402]
            for x, title, sub, zone in zip(xs,
                    ("Writer", "Beacons", "ONA gateway", "Command Post"),
                    ("Detect a hazard", "Save and relay", "Add GPS; forward", "Update map; plan"),
                    ("Inside tunnel", "Inside tunnel", "Tunnel entrance", "Outside team")):
                box(x, 132, 107, title, sub, zone)
            for x in xs[:-1]: arrow(x+107, 157, x+134, 157)
            c.setFillColor(TEAL); c.setFont(BOLD, 10)
            c.drawString(0, 94, "2  SEND A JOB IN; WRITE BACK WHAT HAPPENED")
            for x, title, sub, zone in zip(xs,
                    ("Command Post", "ONA gateway", "Executor", "Beacons"),
                    ("Choose robot; job", "Deliver job brief", "Sense and act", "Save new result"),
                    ("Outside team", "Tunnel entrance", "Inside tunnel", "Inside tunnel")):
                box(x, 29, 107, title, sub, zone)
            for x in xs[:-1]: arrow(x+107, 54, x+134, 54)
            c.setFont(FONT, 8.5); c.setFillColor(MUTED)
            c.drawString(0, 0, "The new result follows flow 1 again. Repeated boxes show the same components.")
        elif self.kind == "packet":
            c.setFillColor(TEAL); c.setFont(BOLD, 10)
            c.drawString(0, 79, "ONE TRANSMITTED FINDING = 39 BYTES")
            x = 0
            sections = [(10, "Mesh header: 10 B", "Routing"),
                        (18, "Finding: 18 B", "What / where / when"),
                        (10, "Memory: 10 B", "State / version"), (1, "", "")]
            for i, (size, title, sub) in enumerate(sections):
                width = WIDTH * size / 39
                c.setFillColor(PALE if i % 2 == 0 else colors.HexColor("#D6EBEE"))
                c.setStrokeColor(TEAL); c.rect(x, 23, width, 43, fill=1, stroke=1)
                c.setFillColor(NAVY); c.setFont(BOLD, 9)
                c.drawCentredString(x+width/2, 48, title)
                c.setFont(FONT, 8.5); c.drawCentredString(x+width/2, 33, sub)
                x += width
            c.setStrokeColor(TEAL); c.line(WIDTH-6.5, 23, WIDTH-6.5, 12)
            c.setFillColor(MUTED); c.setFont(FONT, 8.5)
            c.drawString(0, 4, "Byte order, left to right; base finding includes its own CRC.")
            c.drawRightString(WIDTH, 4, "Outer CRC: 1 B")
        else:
            names = [("1  ROUTE BLOCKED", "Fire robot reports"), ("2  CLEAR RUBBLE", "Debris robot acts"),
                     ("3  CONFIRM CLEAR", "Outside team receives"), ("4  RETRY FIRE JOB", "New attempt ID")]
            for i,(title,sub) in enumerate(names):
                x=i*131
                box(x,65,115,title,sub)
                if i: arrow(x-16,89,x,89)
            c.setFillColor(TEAL); c.setFont(BOLD, 9.5)
            c.drawString(0, 41, "The original job waits until clearance reaches the Command Post.")
            c.setFont(FONT,9);c.setFillColor(MUTED)
            c.drawString(0,23,"Finish only when the hazard record is updated and the response robots return home.")
            c.drawString(0,7,"If delivery, clearance or return fails, the demo stops with a reason; it cannot claim success.")


def header(c, page, title):
    c.setFillColor(NAVY); c.rect(0,H-8,W,8,fill=1,stroke=0)
    c.setFont(BOLD,8.5);c.drawString(MARGIN,H-31,"THE LIVING MAP  /  PHASE 1 TECHNICAL REPORT")
    c.setFont(FONT,8.5);c.drawRightString(W-MARGIN,H-31,"5 OCTOBER 2026")
    c.setFont(BOLD,22);c.drawString(MARGIN,H-66,title)
    c.setStrokeColor(colors.HexColor("#CDDFE3"));c.line(MARGIN,40,W-MARGIN,40)
    c.setFillColor(MUTED);c.setFont(FONT,8)
    c.drawString(MARGIN,26,"TSYP14 | Mines / Tunnels | Software and simulation evidence")
    c.drawRightString(W-MARGIN,26,f"{page} / 6")


def build():
    verified = json.loads((EVIDENCE / "verification.json").read_text())
    for name, digest in verified["source_manifest"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Source changed since verification: {name}")
    scenarios = json.loads((EVIDENCE/"scenarios.json").read_text())["results"]
    extra = json.loads((EVIDENCE/"supplemental.json").read_text())
    assert verified["pytest"]["failures"] == 0 and all(r["passed"] for r in scenarios) and extra["passed"]
    pages = []
    pages.append(("A memory that outlives the robot", [
        p("<b>Spatial Memory for Emergency Robots</b><br/>IEEE RAS x IEEE AESS Tunisia Section - TSYP14 technical challenge", SMALL),
        h("1. Why the project exists; what works now"),
        p("An emergency robot can discover hazards in a tunnel where GPS and direct outside communication are unavailable. If it fails, its private knowledge may be lost. The Living Map saves selected findings in small radio beacons so a later robot can act without restarting exploration from zero."),
        p("<b>Implemented now:</b> autonomous tunnel exploration; FIRE/GAS detection; beacon storage and radio relays; local-to-GPS conversion; outside mission planning; response robots; and recovery after explorer failure or a blocked route. These run in the Python/Pygame simulation. <b>Next steps:</b> physical robots, real radio and sensors, saved data across restarts, and SLAM. No physical prototype or field accuracy is claimed."),
        h("2. How information becomes a mission"),
        Diagram("architecture"),
        Spacer(1, 6),
        p("<b>Figure 1.</b> Read each row left to right. The Command Post chooses the work. The ONA carries information and converts positions. A robot's new observation returns through the same beacon network.", SMALL),
        table([["Component", "Plain-language role and implemented responsibility"],
               ["Writer", "Explorer: discovers its own map, detects events, chooses what to save and where to place a beacon."],
               ["Beacon", "Radio marker: stores records and relays packets toward the entrance, with buffering and retries."],
               ["ONA", "Entrance gateway: validates received data, converts coordinates, forwards findings and delivers briefs."],
               ["Command Post", "Outside team: maintains the Living Map, prioritizes work and chooses a capable, available robot."],
               ["Executor", "Response robot: follows inherited information, senses locally, acts, updates memory and returns."]], [96, WIDTH-96]),
        p("Robots communicate with beacons and the ONA through RobotLink; only the ONA connects to the Command Post. Each robot navigates with its own discovered map. The display can show the full simulation, but robots cannot use that hidden knowledge. Tests check these boundaries. [1, 2]", SMALL),
    ]))
    pages.append(("Explore, decide and preserve", [
        h("3. Autonomous Writer and event decisions"),
        p("The Writer explores the edge of known space, called a <b>frontier</b>. A* route planning uses only the map it has discovered. Local sensors reveal walls and hazards as it moves. A fixed seed repeats the same choices; the route itself is not scripted. The Writer budgets time to return to the entrance. An injected failure tests what happens if it cannot return."),
        p("Position is measured in local metres from the entrance. The demos use ideal simulated movement tracking, not SLAM or calibrated physical sensors. FIRE/GAS findings are saved at severity 2 or above and confidence 50% or above. Nearby same-type findings within two horizontal/vertical grid steps are suppressed. These are test settings, not measured detection thresholds."),
        p("The Writer reuses a nearby beacon with space. With few beacons left, it saves them for important events. If a finding cannot reach the entrance, it moves back toward a connection and places relay beacons using locally measured signal strength. The log explains each decision. [2]"),
        h("4. Beacon type, stored data and radio messages"),
        p("<b>Current type:</b> a programmable, simulated <b>radio memory-and-relay beacon</b> (BeaconNode). An event beacon stores findings; a relay-only beacon bridges a gap and may hold none. Both use the same node design. Default capacity is four findings per beacon. A beacon's ID identifies the host; a memory ID identifies one finding."),
        table([["Part", "Fields", "Bytes"],
               ["Beacon packet", "Host ID; event ID; x/y float32; timestamp uint32; severity; confidence; battery; CRC", "18"],
               ["Memory extension", "Memory ID uint16; version; lifecycle; passage state; latest observation time; source node", "10"],
               ["Mesh envelope", "Type; origin; sequence; TTL; hop count; link source/destination/gradient; length; outer CRC", "11"],
               ["Complete MEMORY frame", "18-byte packet + 10-byte extension + 11-byte envelope", "39"]], [105, WIDTH-150,45]),
        Diagram("packet"),
        p("<b>Figure 2.</b> Header and outer checksum together form the 11-byte mesh envelope. GPS is added later by the ONA; it is absent from this frame.", SMALL),
        p("Each radio hop chooses a neighbour nearer the entrance, waits for acknowledgement and retries if needed. Nodes keep undelivered packets, ignore duplicates and limit the number of hops (TTL). CRC checks damaged bytes. The guided Details view shows actual received bytes, packet size and relay history. [3]"),
        p("<b>Wire detail:</b> the complete finding is 39 bytes. CRC uses MSB-first polynomial 0x31, initial/final XOR zero; test bytes 123456789 give 0xA2. Identifiers and versions have explicit range limits; exhaustion raises an error instead of wrapping.", SMALL),
        p("<b>Planned physical type:</b> Arduino Nano + SX1278/Ra-02 LoRa radio + battery. Real radio transport and durable storage are not implemented. Range, interference, power use and battery life still need measurement. Storage and queues are finite; a simulated acknowledgement proves reception, not a flash-memory write. [2]", SMALL),
    ]))
    pages.append(("Keep memory consistent and useful", [
        h("5. Where the data lives; how it stays trustworthy"),
        p("Inside each beacon, <b>BeaconNode.records</b> holds the event packet and memory extension in RAM. The ONA delivers copies to the Command Post's Living Map. Each finding keeps its latest observation time, confidence, reporting robot and host beacon. The outside map lowers confidence as a report ages, without declaring the hazard gone. An Executor checks the site and saves a fresh observation."),
        table([["Record state", "Meaning for the next mission"],
               ["UNVERIFIED", "A saved report exists, but a response robot has not checked it."],
               ["VERIFIED / ACTIVE", "The report was confirmed; ACTIVE means the hazard still exists."],
               ["CLEARED", "The event or requested obstruction has been resolved."],
               ["CONTRADICTED", "Local sensing did not find the remembered event."],
               ["ESCALATED", "The problem persists and requires further help."]], [130,WIDTH-130]),
        p("Reports of the same event within 0.3 m share <b>one main record</b> (the canonical record). Other IDs remain valid alternate names (aliases). Versions are tracked separately for each incoming ID: a repeated packet is not another confirming observation. Older reports cannot reopen a cleared event; at equal times, a resolved state beats an unverified one. Accepted changes advance the main record's revision. History keeps incoming IDs/versions, and the display follows a finding moved to another host. [2, 4]"),
        h("6. ONA: convert positions and carry information"),
        p("The entrance gateway checks packets, removes duplicates, adds GPS positions and forwards findings. It holds failed outside deliveries for retry. Executors collect job instructions from its mailbox before entering. The Command Post plans the jobs. A software connection stands in for future wireless/satellite communication; no real distant link has been tested."),
        p("Local (0, 0) is the entrance. Heading is counter-clockwise from east. First rotate x/y into east/north metres, then approximate GPS near the entrance. In the equations, theta is heading in radians; ref_lat_rad is reference latitude converted to radians. GPS output is in degrees. [3]"),
        p("east = x cos(theta) - y sin(theta)<br/>north = x sin(theta) + y cos(theta)<br/>latitude = ref_lat + north / 111111<br/>longitude = ref_lon + east / (111111 cos(ref_lat_rad))", CODE),
        Spacer(1, 6),
        p("<b>Recorded example:</b> the normal demo's fire finding at local (2.0, -3.0) m becomes GPS (36.8064730, 10.1815225). GPS is added by the ONA, not transmitted in the 39-byte MEMORY frame. Coordinate tests check axes, headings and round trips. Seven-decimal output precision is not a measured positioning accuracy. [4]", SMALL),
        h("What survives a failure"),
        p("A Writer failure leaves beacon findings available while the simulation runs. Closing the application loses this RAM state. JSON exports let a reviewer inspect results; they do not restore a database. Restart persistence and SLAM remain next steps.", SMALL),
    ]))
    pages.append(("Finish the mission and recover", [
        h("7. Planning and Executor behavior"),
        p("The Command Post chooses urgent, believable and reachable jobs using severity, confidence, report age, hazard type, record state and travel cost. It chooses an available robot with suitable equipment, then prefers more battery and fewer previous jobs. The job brief includes the target, known beacon positions, hazards and instructions for a blocked route. These priority rules are test settings."),
        p("The Executor uses those hints, builds its own local map and changes route when it senses an obstacle. It can put out a simulated fire or investigate gas. It checks the result, updates a beacon, reports the outcome and returns home. Gas investigation leaves the record ACTIVE: the job is finished, but the gas hazard remains. [2]"),
        h("8. Blocked route: clear it, then retry"),
        Diagram("recovery"),
        p("<b>Figure 3.</b> Rubble appears after exploration. The first fire attempt reports a blockage. A DEBRIS robot clears the requested obstruction. Only after the outside team receives clearance does the original fire job retry. Another unrelated blockage may remain recorded under the on-demand policy. [4]", SMALL),
        p("Each dispatch gets a new attempt number, including a retry. A late result for an old attempt cannot finish a newer assignment or make its robot available. Old status also cannot roll back a newer robot state. Each outcome counts once, and each mission appears once in the queue. This prevents duplicate retries. Attempt IDs are positive 16-bit values unique within the running process. Old nine-byte STATUS payloads still decode; the new eleven-byte format adds the attempt ID. Old messages cannot alter a modern assignment. [3, 4]"),
        table([["Failure or uncertainty", "Demonstrated response / honest limit"],
               ["Writer fails after saving", "Beacon findings survive; response robots still complete their jobs."],
               ["Rubble blocks a route", "Blocked job requests clearance, then retries once as a new attempt."],
               ["Event no longer present", "Executor sensing writes CONTRADICTED, rather than trusting the old report."],
               ["Relay interrupted", "A stored record remains during disconnection and arrives after reconnection."],
               ["Missing delivery, fault, low battery", "Unfinished acceptance checks time out with a readable stop reason."],
               ["Conflicting final copies / extra retry", "All final checks are required; a failed check cannot display success."]], [165,WIDTH-165]),
        p("Eleven injected failures exercise early explorer loss, outside delivery loss, missing briefs, unavailable clearance, fault, low battery, stranding, conflicting copies, extra retry, missing return and runtime error. The controller stops and cannot silently resume; R resets it. These tests show correct failure reporting, not recovery from every possible fault. [4]", SMALL),
    ]))
    result_rows = [["Guided scenario (seed 42)", "Outcome", "Final tick"]]
    result_rows += [[r["scenario"], "All acceptance checks PASS", r["tick"]] for r in scenarios]
    comparison_rows = [["Seed", "Travel: memory", "Travel: baseline", "Ticks: memory", "Ticks: baseline"]]
    for r in extra["comparison"]["runs"]:
        comparison_rows.append([r["seed"], r["memory"]["outbound_cells"], r["baseline"]["outbound_cells"],
                                r["memory"]["mission_ticks"], r["baseline"]["mission_ticks"]])
    pages.append(("Validation and actual results", [
        h("9. What we checked"),
        p(f"The recorded full suite has <b>{verified['pytest']['tests']} passing tests</b>, zero failures, errors or skips ({verified['pytest']['seconds']:.3f} s). It used Python 3.13.5, pytest 9.1.1 and Pygame 2.6.1. Tests cover alternate IDs, duplicate/old reports, moved hosts, late/repeated outcomes, retry uniqueness, both status formats and range limits. Runtime source hashes still match the tested files. [4]"),
        table(result_rows, [185,WIDTH-255,70]),
        Spacer(1,8),
        p("A demo passes only when expected records arrive, dispatched jobs finish, response robots return and become available, queues contain no duplicate or eligible pending work, and beacon copies agree with the outside map. The network runs for sixty more stable simulation steps to catch late updates. Missing results stop the demo with a reason."),
        p("Automated Windows input checked phase advance, pause/resume, reset, scenario switching, Jobs/Findings, Details, selection and scrolling. Captures were inspected for readable, unclipped content. This is automated UI verification, not a human walkthrough."),
        h("10. Does inherited memory help? Six-seed comparison"),
        table(comparison_rows, [43,116,116,116,WIDTH-391]),
        Spacer(1,8),
        p("Travel counts grid cells on the outward trip; ticks count simulation steps, not real seconds. Baseline means the robot starts without inherited memory. Each pair uses the same arena and debris; all twelve runs reached their targets. New debris is unknown to both robots. Seeds 45 and 47 have equal travel, so memory does not improve every layout. [4]"),
        h("11. Old reports, missing events and broken relays"),
        p("The aging check reduced live confidence from 39% to 5% after a 1200-second simulated-time jump while retaining UNVERIFIED. Local Executor intervention refreshed the record to 91% confidence and CLEARED. A separate missing-event test produced CONTRADICTED through sensing. The four-hop relay fixture retained the deepest record during an outage and delivered it after reconnection; the seed-5 global demo formed a seven-hop chain. [4]"),
        p("<b>Reproducible identity.</b> Base " + verified["base_revision"][:12] + " plus local changes. Full revision, source fingerprint and per-file SHA-256 hashes: audit/phase1/verification.json. [4]", SMALL),
    ]))
    pages.append(("Technical synthesis and development", [
        h("12. Phase 1 technical contribution"),
        p("Phase 1 establishes a complete information loop in simulation: the Writer explores and preserves FIRE/GAS findings; beacons store and relay them; the ONA converts positions and exchanges information with the Command Post; and Executors use that knowledge to complete missions and update the map. The demonstrated recovery cases preserve useful findings after Writer failure and restore access when debris blocks a mission. [2, 4]"),
        p("The central contribution is the selective sharing of operational knowledge between successive robots. Versioned observations, report aging and local verification keep that knowledge useful as the environment changes. The three diagrams describe the architecture, transmitted data and recovery sequence; the results on page 5 establish the current software validation. These results concern the modeled tunnel and simulated sensing, movement and radio."),
        h("13. Physical integration and experimental validation"),
        p("The proposed hardware stage retains the existing division of responsibilities. ESP32 controllers are planned for two robots and the ONA; Arduino Nano controllers with SX1278/Ra-02 radios are planned for the beacons. Component quantities and wiring will first be reconciled, followed by power, motor, encoder, event-sensor and beacon-deployment tests. Physical assembly and calibration remain to be completed. [2]"),
        p("Radio integration will implement the current packet format over LoRa and add storage that survives a beacon restart. Tests will examine delivery through several relays, interruption and reconnection, and retention of saved findings. The complete missions will then be repeated on physical robots, recording delivery rate, range, battery use, detection performance and position error. Successful validation requires confirmed observations, completed dispatched jobs and robot return, as in the simulation."),
        h("14. Localization and mapping with SLAM"),
        p("A further development is <b>Simultaneous Localization and Mapping (SLAM)</b>: estimating the robot's position while building a map in the GPS-denied tunnel. The present demonstrations use ideal simulated movement tracking; SLAM is not yet implemented. Candidate sensing will combine lidar or camera observations with encoders and an inertial sensor. Sensor suitability and computing requirements will be evaluated before selecting the hardware."),
        p("An initial mapping prototype will be compared with a known layout to measure position drift and map consistency. Its position and map outputs will then feed the existing navigation interfaces. SLAM will support geometric localization, while beacons will continue preserving hazard reports and mission observations. This extension therefore complements the Living Map's operational memory."),
        h("15. Reproducibility and supporting material"),
        p("The repository README provides installation, guided controls and headless execution instructions. The normal demonstration can be launched from the repository root using the configured Python environment:", SMALL),
        p("python -B run_simulation.py --guided --scenario normal --seed 42", CODE),
        p("The same entry point supports writer-failure and debris-recovery. Source hashes, automated results and captures are retained in audit/phase1/. Execution was verified on Windows; README also provides macOS/Linux setup instructions. [4]", SMALL),
        p("<b>References.</b> [1] TSYP14, The Living Map: Spatial Memory for Emergency Robots, challenge brief, pp. 1-3. [2] Project implementation; docs/architecture/system-architecture.md; hardware/README.md. [3] common/protocol.py; common/coordinates.py; docs/communication/beacon-protocol.md. [4] audit/phase1/{verification.json, pytest.xml, scenarios.json, supplemental.json, ui/}; docs/phase1_demo.md; docs/phase1_traceability.md. Repository: github.com/abdelkqder/The-Living-Map-TSYP14.", SMALL),
    ]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("The Living Map - Phase 1 Technical Report")
    c.setAuthor("The Living Map project")
    c.setSubject("TSYP14 Mines / Tunnels: six-page simulation, verification and implementation report")
    for n,(title,flowables) in enumerate(pages,1):
        header(c,n,title)
        frame=Frame(MARGIN,51,WIDTH,H-134,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        frame.addFromList(flowables,c)
        if flowables:
            raise RuntimeError(f"Page {n} overflow: {len(flowables)} items remain; shorten content before delivering")
        c.showPage()
    c.save()
    print(OUT)


if __name__ == "__main__":
    build()
