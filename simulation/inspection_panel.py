"""Scrollable Mission/Memory inspector for the existing Pygame renderer."""
import textwrap
import pygame

from simulation.jury_demo import SCENARIOS


class InspectionPanel:
    def __init__(self, renderer, session=None):
        self.r = renderer
        self.session = session
        self.tab = "Mission"
        self.scroll = 0
        self.content_lines = []
        self.visible_lines = []
        self.details = False

    def toggle_details(self):
        self.details = not self.details
        self.scroll = 0

    def reset(self, name=None):
        self.session.reset(name)
        self.r.sys = self.session.system
        self.r._selected = None
        self.scroll = 0

    def set_tab(self, tab):
        self.tab, self.scroll = tab, 0

    def draw(self):
        from simulation.renderer import PANEL_BG, PANEL_BORDER, TEXT_BRIGHT, TEXT_MAIN, TEXT_DIM, SUCCESS, HEADER_BG, BTN_H, BTN_GAP
        r, s = self.r, self.session
        x, y, width = r.map_w+16, 14, r.panel_w-32
        pygame.draw.rect(r.screen, PANEL_BG, pygame.Rect(r.map_w, 0, r.panel_w, r.h))
        pygame.draw.line(r.screen, PANEL_BORDER, (r.map_w,0), (r.map_w,r.h), 2)
        r.screen.blit(r.font_big.render("THE LIVING MAP", True, TEXT_BRIGHT), (x,y))
        y += 28
        lines = [f"Mines / Tunnels | SIMULATION | tick {r.sys.tick}"]
        names = {"normal": "Normal response", "writer-failure": "Explorer failure and saved findings", "debris-recovery": "Blocked route, clearance and retry"}
        lines += [f"{names[s.name]} | seed {s.seed}"] if s else [r.sys.phase.upper()]
        for line in lines:
            for part in textwrap.wrap(line, 56):
                r.screen.blit(r.font_sm.render(part, True, TEXT_MAIN), (x,y))
                y += 17
        y += 6
        half = (width-8)//2
        if s:
            r._btn(x, y, half, "SPACE  CONTINUE", SUCCESS, s.advance, not s.done and not s.error)
            y = r._btn(x+half+8, y, half, "P  RESUME" if s.paused else "P  PAUSE",
                       (74,82,100), s.toggle_pause, not s.done and not s.error)
            bw = (width-16)//3
            for i, (name, label) in enumerate(zip(SCENARIOS, ("1 NORMAL", "2 EXPLORER FAIL", "3 BLOCKED ROUTE"))):
                r._btn(x+i*(bw+8), y, bw, label, (33,103,199), lambda n=name: self.reset(n), True)
            y += BTN_H+BTN_GAP
        else:
            actions = [("W WRITER",r.sys.deploy_writer), ("E EXECUTOR",r.sys.dispatch_executor),
                       ("D REPLACEMENT",r.sys.deploy_replacement_writer), ("AUTO ON/OFF",r._toggle_auto),
                       ("P PAUSE/RESUME",r._toggle_pause), ("X DEBRIS",r.drop_random_debris)]
            for i,(label,action) in enumerate(actions):
                r._btn(x+(i%2)*(half+8), y+(i//2)*(BTN_H+BTN_GAP), half, label, (74,82,100), action, True)
            y += 3*(BTN_H+BTN_GAP)
        if s:
            story = s.explanation()
            color = (255,125,125) if s.error else SUCCESS if s.done else TEXT_BRIGHT
            for label, value in (("", story["title"]), ("Now: ", story["what"]),
                                 ("Why: ", story["why"]), ("Next: ", story["next"])):
                for part in textwrap.wrap(label+value, 56):
                    r.screen.blit(r.font_sm.render(part, True, color if not label else TEXT_MAIN), (x,y))
                    y += 17
            y += 9
        bw = (width-16)//3
        for i,tab in enumerate(("Mission","Memory")):
            r._btn(x+i*(bw+8), y, bw, "JOBS" if tab=="Mission" else "FINDINGS", SUCCESS if self.tab==tab else (100,108,124),
                   lambda t=tab: self.set_tab(t), True)
        r._btn(x+2*(bw+8), y, bw, "T DETAILS: " + ("ON" if self.details else "OFF"),
               SUCCESS if self.details else (100,108,124), self.toggle_details, True)
        y += BTN_H+12
        rows = self.mission_lines() if self.tab=="Mission" else self.memory_lines()
        self.content_lines = [(part,mid) for text,mid in rows for part in (textwrap.wrap(text,56) or [""])]
        capacity = max(1,(r.h-45-y)//17)
        self.scroll = max(0,min(self.scroll,max(0,len(self.content_lines)-capacity)))
        self.visible_lines = self.content_lines[self.scroll:self.scroll+capacity]
        for text,mid in self.visible_lines:
            if mid is not None:
                rect = pygame.Rect(x-4,y-1,width+8,17)
                if mid==r._selected:
                    pygame.draw.rect(r.screen,HEADER_BG,rect)
                r._buttons.append((rect,lambda m=mid:r._select(m)))
            r.screen.blit(r.font_sm.render(text,True,TEXT_MAIN),(x,y))
            y += 17
        r.screen.blit(r.font_sm.render("R restart | Tab view | T details | wheel scroll",True,TEXT_DIM),(x,r.h-33))
        if len(self.content_lines)>capacity:
            r.screen.blit(r.font_sm.render(f"Rows {self.scroll+1}-{self.scroll+len(self.visible_lines)} / {len(self.content_lines)}",True,TEXT_DIM),(x,r.h-17))

    def mission_lines(self):
        if self.details:
            rows = self._mission_details()
            if self.session and self.session.error_detail:
                rows = [("STOP DIAGNOSTIC: " + self.session.error_detail,None)] + rows
            return rows
        from simulation.demo_language import ROBOT_STATES, MISSION_STATES
        sys = self.r.sys
        rows = [("EXPLORER: searches and saves findings",None)]
        for w in sys.writers:
            state = "failed; saved findings remain" if w.dead and not w.returned else "returned to the entrance" if w.returned else "exploring the tunnel"
            rows.append((f"{w.writer_id}: {state}. Findings saved: {w.memory_count}.",None))
        rows += [("",None),("RESPONSE ROBOTS: check and handle hazards",None)]
        for e in sys.command_post.fleet.all():
            rows.append((f"{e.executor_id} ({e.capabilities[0].value.lower()} equipment): {ROBOT_STATES.get(e.state.value,e.state.value.lower().replace('_',' '))}. Battery {e.battery_pct}%.",None))
        rows += [("",None),("JOBS CHOSEN BY THE OUTSIDE COMMAND TEAM",None)]
        if not sys.command_post.mission_table():
            rows.append(("Waiting for saved findings to reach the outside team.",None))
        for m in sys.command_post.mission_table():
            rows.append((f"{m.event_type.lower()} job {m.mission_id}: {MISSION_STATES.get(m.status.value,m.status.value.lower().replace('_',' '))}. Robot {m.assigned_executor_id or 'not assigned'}; attempt {m.attempt_id}.",None))
        for d in sys.command_post.decisions[-2:]:
            choice = d['selection']
            equipment = ("specialist equipment for this job" if choice['match'].startswith('specialist')
                         else "general equipment that can handle this job")
            rows.append((f"Chosen {d['executor']}: {equipment}; battery {choice['battery_pct']}%; {choice['missions_done']} earlier jobs finished.",None))
        rows += [("",None),("Details shows the actual planning scores, robot states and job messages.",None)]
        return rows

    def _mission_details(self):
        sys=self.r.sys
        rows=[("WRITER: autonomy and preservation",None)]
        for w in sys.writers:
            rows += [(f"{w.writer_id} {w.state.value} | coverage {100*w.discovered.coverage_ratio(sys.total_free_cells):.0f}% | memories {w.memory_count}",None),
                     (f"Odometry ({w.pose.x:.2f}, {w.pose.y:.2f}) m | frontiers selected {w.stats['frontiers_selected']}",None)]
            if w.decisions:
                d=w.decisions[-1]
                rows += [(f"Preservation: {d['event']} / {d['decision']}: {d['reason']}",None)]
        rows += [("",None),("EXECUTORS / MISSIONS",None)]
        for e in sys.command_post.fleet.all():
            rows += [(f"{e.executor_id} {e.capabilities[0].value}: {e.state.value} | attempt {e.attempt_id} | battery {e.battery_pct}%",None)]
        for m in sys.command_post.mission_table():
            rows += [(f"{m.mission_id} {m.event_type} #{m.beacon_id:04X}: {m.status.value} | attempt {m.attempt_id} | {m.assigned_executor_id or '-'}",None)]
        rows += [("",None),("COMMAND POST: latest actual decisions",None)]
        for d in sys.command_post.decisions[-2:]:
            c=d['components']
            rows += [(f"t={d['tick']} {d['mission_id']} / attempt {d['attempt_id']} -> {d['executor']} priority {d['priority']}",None),
                     (f"Why: {d['selection']['why']}",None),
                     (f"Base {c['base']} x class {c['class_weight']} x state {c['status_factor']} - travel {c['travel_penalty']} + blocker {c['blocker_boost']}",None)]
        rows += [("",None),("LATEST MISSION EVENTS",None)]
        rows += [(line,None) for line in sys.command_post.log[-3:]]
        if self.session and self.session.done:
            rows += [(f"Acceptance: {'PASS' if all(self.session.checks().values()) else 'FAIL'}",None)]
        return rows

    def memory_lines(self):
        if self.details:
            return self._memory_details()
        from simulation.demo_language import MEMORY_STATES
        sys,r = self.r.sys,self.r
        records = sys.living_map.all()
        if r._selected is None and records:
            r._selected = records[0].memory_id
        rows = [("SAVED FINDINGS: click a finding to inspect it",None)]
        for rec in records:
            rows.append((f"Finding {rec.memory_id}: {rec.event_type.lower()} - {MEMORY_STATES[rec.state.value]}",rec.memory_id))
        rec = sys.living_map.get(r._selected) if r._selected is not None else None
        if rec:
            rows += [("",None),(f"Finding {rec.memory_id}: {MEMORY_STATES[rec.state.value]}.",None),
                     (f"Last observation {rec.age_seconds:.1f} seconds ago; confidence {rec.confidence_pct}%.",None),
                     (f"Saved at radio marker {rec.host_beacon_id}; received from {rec.source}.",None),
                     ("Confidence can fall with age. That alone does not mean the hazard has gone away.",None),
                     (f"Tunnel position: ({rec.x_local:.2f}, {rec.y_local:.2f}) metres.",None)]
            if rec.gps_lat is not None:
                rows.append((f"Entrance gateway converts this to GPS: {rec.gps_lat:.7f}, {rec.gps_lon:.7f}.",None))
            packet = self.session.packet_for(rec) if self.session else None
            if packet:
                rows.append((f"Actual radio message: {packet['bytes']} bytes; passed through {packet['hops']} radio hops.",None))
        rows += [("",None),(f"Entrance gateway: {sys.ona.mesh_stats['memory']} finding messages received; {sys.ona.buffered_count} waiting to be forwarded.",None),
                 ("Details shows IDs, update history, packet bytes and radio links.",None)]
        return rows

    def _memory_details(self):
        sys,r=self.r.sys,self.r
        records=sys.living_map.all()
        if r._selected is None and records:
            r._selected=records[0].memory_id
        rows=[("LIVING MAP: select a record",None)]
        for rec in records:
            rows += [(f"#{rec.memory_id:04X} {rec.event_type}: {rec.state.value} v{rec.version} | host B{rec.host_beacon_id}",rec.memory_id)]
        rec=sys.living_map.get(r._selected) if r._selected is not None else None
        if rec:
            gps=f"({rec.gps_lat:.7f}, {rec.gps_lon:.7f})" if rec.gps_lat is not None else "awaiting ONA translation"
            rows += [("",None),(f"SELECTED #{rec.memory_id:04X} | aliases {rec.aliases or 'none'}",None),
                     (f"Lifecycle {rec.state.value} | revision {rec.version} | stale {rec.is_stale}",None),
                     (f"Age {rec.age_seconds:.1f}s | confidence {rec.confidence_pct}% | severity {rec.severity}",None),
                     (f"Source {rec.source} (node {rec.source_node}) | host B{rec.host_beacon_id}",None),
                     (f"Created {rec.timestamp} | observation {rec.observed_ts}",None),
                     (f"Local ({rec.x_local:.3f}, {rec.y_local:.3f}) m",None),(f"ONA GPS {gps}",None)]
            packet=self.session.packet_for(rec) if self.session else None
            if packet:
                rows += [("",None),(f"ACTUAL RECEIVED FRAME: {packet['bytes']} bytes | tick {packet['tick']}",None),
                         (f"origin {packet['origin']} -> relay {packet['src']} -> ONA | hops {packet['hops']} | seq {packet['seq']}",None),
                         (f"Wire memory #{packet['memory_id']:04X} v{packet['version']} {packet['state']}",None),(packet['hex'],None)]
            rows += [("",None),("OBSERVATION HISTORY",None)]
            rows += [(line,None) for line in rec.history[-2:]]
        rows += [("",None),(f"ONA: memory {sys.ona.mesh_stats['memory']} | buffered {sys.ona.buffered_count} | briefs delivered {sys.ona.briefs_delivered}",None),
                 ("BEACON RELAYS (radio links, not walking paths)",None)]
        for bid,node in sorted(sys.beacons.nodes.items()):
            rows += [(f"B{bid}: records {len(node.records)} | parent {node.parent} | hops {node.hops} | {node.comm_state()}",None)]
        return rows

    def handle_event(self,ev):
        if ev.type==pygame.QUIT:
            return False
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            self.r.handle_click(ev.pos)
        elif ev.type==pygame.MOUSEWHEEL:
            self.scroll=max(0,self.scroll-ev.y*3)
        elif ev.type==pygame.KEYDOWN:
            if ev.key in (pygame.K_q,pygame.K_ESCAPE):
                return False
            if ev.key==pygame.K_TAB:
                self.set_tab("Memory" if self.tab=="Mission" else "Mission")
            elif ev.key==pygame.K_t:
                self.toggle_details()
            elif ev.key in (pygame.K_UP,pygame.K_DOWN):
                self.scroll=max(0,self.scroll+(-3 if ev.key==pygame.K_UP else 3))
            elif self.session:
                if ev.key==pygame.K_SPACE:
                    self.session.advance()
                elif ev.key==pygame.K_p:
                    self.session.toggle_pause()
                elif ev.key==pygame.K_r:
                    self.reset()
                elif ev.key in (pygame.K_1,pygame.K_2,pygame.K_3):
                    self.reset(SCENARIOS[ev.key-pygame.K_1])
        return True
