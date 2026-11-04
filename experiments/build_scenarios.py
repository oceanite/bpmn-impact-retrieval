"""Rebuild the evaluation scenarios S01-S06 in data/bpmn/scenarios/.

Each scenario starts from one of Simple-ERP's English level-2 models
(data/target_repo/docs/bpmn, verified at commit c76a313) and applies a scripted
change. old.bpmn and new.bpmn are both written through the same serializer, so a
plain text diff shows only the intended change. Re-running gives identical output.

Usage (from the repo root):
    python experiments/build_scenarios.py [<simple-erp docs/bpmn dir> <output scenarios dir>]

This is a data-preparation script, not part of the retrieval pipeline.
The answer key for these scenarios lives in data/ground_truth/ground_truth.csv.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
for p, u in NS.items():
    ET.register_namespace(p, u)
B, BDI, DC, DI = (f"{{{NS[k]}}}" for k in ("bpmn", "bpmndi", "dc", "di"))


class Model:
    def __init__(self, path):
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()

    # ---- lookup -------------------------------------------------------
    def el(self, id_):
        for e in self.root.iter():
            if e.get("id") == id_:
                return e
        raise KeyError(id_)

    def parent(self, child):
        for p in self.root.iter():
            if child in list(p):
                return p
        raise KeyError(child)

    def shape(self, id_):
        for s in self.root.iter(BDI + "BPMNShape"):
            if s.get("bpmnElement") == id_:
                return s
        return None

    def edge(self, id_):
        for s in self.root.iter(BDI + "BPMNEdge"):
            if s.get("bpmnElement") == id_:
                return s
        return None

    def bounds(self, id_):
        b = self.shape(id_).find(DC + "Bounds")
        return {k: float(b.get(k)) for k in ("x", "y", "width", "height")}

    def process(self):
        return self.root.find(B + "process")

    def plane(self):
        return self.root.find(f"{BDI}BPMNDiagram/{BDI}BPMNPlane")

    # ---- edits --------------------------------------------------------
    def rename(self, id_, name):
        self.el(id_).set("name", name)

    def document(self, id_, text):
        e = self.el(id_)
        doc = e.find(B + "documentation")
        if doc is None:
            doc = ET.Element(B + "documentation")
            e.insert(0, doc)
        doc.text = text

    def retag(self, id_, tag):
        self.el(id_).tag = B + tag

    def move_lane(self, id_, src, dst):
        for lane_id in (src, dst):
            lane = self.el(lane_id)
            refs = [r for r in lane.findall(B + "flowNodeRef") if r.text == id_]
            if lane_id == src:
                for r in refs:
                    lane.remove(r)
            else:
                ET.SubElement(lane, B + "flowNodeRef").text = id_
        lane_b, node = self.bounds(dst), self.shape(id_).find(DC + "Bounds")
        node.set("y", str(int(lane_b["y"] + (lane_b["height"] - float(node.get("height"))) / 2)))

    def _unlink(self, flow_id):
        for e in self.root.iter():
            for ref in list(e):
                if ref.tag in (B + "incoming", B + "outgoing") and ref.text == flow_id:
                    e.remove(ref)

    def remove(self, id_):
        """Remove a node plus every flow touching it, and their DI."""
        for f in [f for f in self.root.iter() if f.tag in (B + "sequenceFlow", B + "messageFlow")
                  and id_ in (f.get("sourceRef"), f.get("targetRef"))]:
            self.remove_flow(f.get("id"))
        e = self.el(id_)
        self.parent(e).remove(e)
        for lane in self.root.iter(B + "lane"):
            for r in [r for r in lane.findall(B + "flowNodeRef") if r.text == id_]:
                lane.remove(r)
        s = self.shape(id_)
        if s is not None:
            self.plane().remove(s)

    def remove_flow(self, flow_id):
        f = self.el(flow_id)
        self.parent(f).remove(f)
        self._unlink(flow_id)
        e = self.edge(flow_id)
        if e is not None:
            self.plane().remove(e)

    def retarget(self, flow_id, new_target):
        f = self.el(flow_id)
        old = self.el(f.get("targetRef"))
        for r in [r for r in old.findall(B + "incoming") if r.text == flow_id]:
            old.remove(r)
        f.set("targetRef", new_target)
        self._add_ref(new_target, "incoming", flow_id)
        self._route(flow_id)

    def _add_ref(self, node_id, kind, flow_id):
        node = self.el(node_id)
        ref = ET.Element(B + kind)
        ref.text = flow_id
        # keep incoming before outgoing, after documentation
        idx = len([c for c in node if c.tag in (B + "documentation", B + "incoming")]) \
            if kind == "incoming" else len(node)
        node.insert(idx, ref)

    def add_flow(self, flow_id, src, tgt, name=None):
        f = ET.Element(B + "sequenceFlow", {"id": flow_id, "sourceRef": src, "targetRef": tgt})
        if name:
            f.set("name", name)
        self.process().append(f)
        self._add_ref(src, "outgoing", flow_id)
        self._add_ref(tgt, "incoming", flow_id)
        edge = ET.SubElement(self.plane(), BDI + "BPMNEdge", {"id": f"{flow_id}_di", "bpmnElement": flow_id})
        self._route(flow_id, edge)

    def rename_flow(self, flow_id, name, condition=None):
        """Change a sequence flow's label and (optionally) its condition expression."""
        f = self.el(flow_id)
        f.set("name", name)
        if condition is not None:
            cond = f.find(B + "conditionExpression")
            if cond is None:
                cond = ET.SubElement(f, B + "conditionExpression",
                                     {f"{{{NS['xsi']}}}type": "bpmn:tFormalExpression"})
            cond.text = condition

    def add_message_flow(self, flow_id, src, tgt, name):
        """Message flow between a task and a participant pool, drawn as a vertical line."""
        collab = self.root.find(B + "collaboration")
        last = max(i for i, c in enumerate(collab) if c.tag in (B + "participant", B + "messageFlow"))
        collab.insert(last + 1, ET.Element(B + "messageFlow",
                                           {"id": flow_id, "name": name, "sourceRef": src, "targetRef": tgt}))
        s, t = self.bounds(src), self.bounds(tgt)
        task, pool = (s, t) if s["height"] < t["height"] or s["width"] < t["width"] else (t, s)
        x = int(task["x"] + task["width"] / 2)
        top, bottom = int(pool["y"] + pool["height"]), int(task["y"])
        ys = (bottom, top) if task is s else (top, bottom)
        edge = ET.SubElement(self.plane(), BDI + "BPMNEdge", {"id": f"{flow_id}_di", "bpmnElement": flow_id})
        for y in ys:
            ET.SubElement(edge, DI + "waypoint", {"x": str(x), "y": str(y)})

    def add_node(self, tag, id_, name, lane, x, w=120, h=80):
        node = ET.Element(B + tag, {"id": id_, "name": name})
        self.process().append(node)
        ET.SubElement(self.el(lane), B + "flowNodeRef").text = id_
        lb = self.bounds(lane)
        sh = ET.SubElement(self.plane(), BDI + "BPMNShape", {"id": f"{id_}_di", "bpmnElement": id_})
        ET.SubElement(sh, DC + "Bounds", {"x": str(x), "y": str(int(lb["y"] + (lb["height"] - h) / 2)),
                                          "width": str(w), "height": str(h)})

    def _route(self, flow_id, edge=None):
        """Orthogonal route: source right-middle -> elbow -> target left-middle."""
        edge = edge if edge is not None else self.edge(flow_id)
        f = self.el(flow_id)
        s, t = self.bounds(f.get("sourceRef")), self.bounds(f.get("targetRef"))
        x1, y1 = s["x"] + s["width"], s["y"] + s["height"] / 2
        x2, y2 = t["x"], t["y"] + t["height"] / 2
        if x2 <= x1:  # target not to the right: enter from top/bottom
            x1, x2 = s["x"] + s["width"] / 2, t["x"] + t["width"] / 2
            y1 = s["y"] + (s["height"] if y2 > y1 else 0)
            y2 = t["y"] if y2 > y1 else t["y"] + t["height"]
            pts = [(x1, y1), (x1, (y1 + y2) / 2), (x2, (y1 + y2) / 2), (x2, y2)]
        else:
            mx = (x1 + x2) / 2
            pts = [(x1, y1), (mx, y1), (mx, y2), (x2, y2)]
        for wp in edge.findall(DI + "waypoint"):
            edge.remove(wp)
        label = edge.find(BDI + "BPMNLabel")
        for x, y in pts:
            wp = ET.Element(DI + "waypoint", {"x": str(int(x)), "y": str(int(y))})
            edge.insert(len(edge.findall(DI + "waypoint")), wp)
        if label is not None:
            edge.remove(label)

    def write(self, path):
        ET.indent(self.tree, space="  ")
        self.tree.write(path, encoding="UTF-8", xml_declaration=True)


# ---------------------------------------------------------------------------
def s01(m):  # P2P: zero-tolerance three-way match -> tolerance-based match
    m.rename("PUR-INV-002", "Validate invoice match within price tolerance")
    m.document("PUR-INV-002", "Compare supplier invoice lines with purchase order lines. "
               "Quantity must match exactly; unit price may differ within the configured "
               "price tolerance percentage instead of requiring an exact match.")
    m.rename("GW-P2P-MATCHED", "Invoice within tolerance?")


def s02(m):  # INV: drop the admin review step; submitted adjustments go straight on
    m.retarget("FLOW-INV-003", "GW-INV-DIFFERENCE")
    for n in ("INV-ADJ-003", "GW-INV-APPROVED", "INV-END-REJECTED"):
        m.remove(n)
    m.document("INV-ADJ-002", "Operator submits the inventory adjustment. Without a separate "
               "admin review or approval, the submitted adjustment proceeds directly to posting.")


def s03(m):  # O2C: drop the explicit customer confirmation step
    m.retarget("FLOW-O2C-008", "GW-O2C-DELIVERY-MERGE")
    m.remove("SAL-SO-005")  # also removes MSG-O2C-002 and FLOW-O2C-010
    m.document("SAL-DLV-001", "Create a delivery directly from an approved sales order; "
               "the order no longer needs a separate confirmation before delivery.")


def s04(m):  # AUTH: password reset no longer revokes existing sessions
    m.rename("AUTH-PWD-005", "Consume password reset token")
    m.document("AUTH-PWD-005", "Consume the reset token and update the password hash. "
               "Existing user sessions stay active; they are no longer revoked on reset.")


def s05(m):  # AUTH: manual link sharing by admin -> automatic invitation email
    m.retag("AUTH-USR-003", "serviceTask")
    m.rename("AUTH-USR-003", "Send invitation link by email")
    m.move_lane("AUTH-USR-003", "LANE-AUTH-ADMIN", "LANE-AUTH-SYSTEM")
    m.document("AUTH-USR-003", "The system emails the invitation link to the invited user "
               "and marks the invitation as shared; the admin no longer copies the token manually.")
    for f in ("FLOW-AUTH-005", "FLOW-AUTH-006"):
        m._route(f)


def s06(m):  # P2P: add an approval step between receiving and posting goods
    m.add_node("userTask", "PUR-GR-003", "Approve goods receipt", "LANE-P2P-ADMIN", x=1240)
    m.document("PUR-GR-003", "Admin reviews the draft goods receipt quantities and approves "
               "it before the receipt is posted to stock.")
    m.retarget("FLOW-P2P-009", "PUR-GR-003")
    m.add_flow("FLOW-P2P-009A", "PUR-GR-003", "PUR-GR-002")


# --- test set (frozen 2026-11-04; do not tune on these) ----------------------
def s07(m):  # O2C: gateway condition - accept backorders instead of blocking on stock
    m.rename("GW-O2C-STOCK", "Stock available or backorder accepted?")
    m.document("GW-O2C-STOCK", "A sales order with insufficient stock may still be submitted and "
               "approved when the customer accepts a backorder; the shortfall is delivered later "
               "as a partial delivery.")
    m.rename_flow("FLOW-O2C-004", "Available or backorder",
                  "stockAvailable = true or backorderAccepted = true")


def s08(m):  # P2P: new message flow - send an invoice dispute notice to the supplier
    m.add_message_flow("MSG-P2P-005", "PUR-INV-003", "PART-P2P-SUPPLIER", "Invoice dispute notice")
    m.document("PUR-INV-003", "Admin records the dispute reason together with the corrected invoice "
               "lines; the reason is sent to the supplier as an invoice dispute notice.")


def s09(m):  # P2P: lane change only - purchase orders are created by the admin, not the operator
    m.move_lane("PUR-PO-001", "LANE-P2P-OPERATOR", "LANE-P2P-ADMIN")
    for f in ("FLOW-P2P-005", "FLOW-P2P-007"):
        m._route(f)


def s10(m):  # O2C: multi-change - supervisor posts deliveries, invoices per delivery
    m.retag("SAL-DLV-002", "userTask")
    m.rename("SAL-DLV-002", "Approve and post delivery")
    m.move_lane("SAL-DLV-002", "LANE-O2C-SYSTEM", "LANE-O2C-ADMIN")
    m.document("SAL-DLV-002", "A supervisor checks the delivery and posts it to stock; the operator "
               "who created the delivery cannot post it.")
    for f in ("FLOW-O2C-011", "FLOW-O2C-012"):
        m._route(f)
    m.rename("SAL-INV-001", "Generate sales invoice per delivery")
    m.document("SAL-INV-001", "Invoice the delivered quantity that is not invoiced yet after each "
               "posted delivery, so partially delivered sales orders can be invoiced.")


SCENARIOS = {
    "S01": ("l2-procure-to-pay.bpmn", s01),
    "S02": ("l2-inventory-adjustment.bpmn", s02),
    "S03": ("l2-order-to-cash.bpmn", s03),
    "S04": ("l2-access-lifecycle.bpmn", s04),
    "S05": ("l2-access-lifecycle.bpmn", s05),
    "S06": ("l2-procure-to-pay.bpmn", s06),
    "S07": ("l2-order-to-cash.bpmn", s07),
    "S08": ("l2-procure-to-pay.bpmn", s08),
    "S09": ("l2-procure-to-pay.bpmn", s09),
    "S10": ("l2-order-to-cash.bpmn", s10),
}

if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    if len(sys.argv) == 3:
        src, out = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        src, out = repo / "data/target_repo/docs/bpmn", repo / "data/bpmn/scenarios"
    for sid, (fname, edit) in SCENARIOS.items():
        d = out / sid
        d.mkdir(parents=True, exist_ok=True)
        Model(src / fname).write(d / "old.bpmn")
        m = Model(src / fname)
        edit(m)
        m.write(d / "new.bpmn")
        print(f"{sid}: {fname} -> {d}")
