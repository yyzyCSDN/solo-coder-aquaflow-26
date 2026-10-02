import unittest
from datetime import datetime,timezone
from decimal import Decimal
from aquaflow.api import AquaFlowService
from aquaflow.lab.revisions import Result,current
from aquaflow.treatment.chlorine_ct import Segment
from aquaflow.network.isolation import Pipe
from aquaflow.meters.balance import Meter
from aquaflow.simulation.hydraulics import Node,Link,solve
class T(unittest.TestCase):
    def test_health(self):self.assertEqual(AquaFlowService().health()["runtime_dependencies"],0)
    def test_ct(self):self.assertTrue(AquaFlowService().ct([Segment(20,1,.8,20)],10))
    def test_isolation(self):
        self.assertEqual(AquaFlowService().isolate({"S","A","B"},[Pipe("1","S","A"),Pipe("2","A","B")],{"2"},{"S"}),{"B"})
    def test_balance(self):
        i=[Meter("i",Decimal(0),Decimal(20),Decimal(1))]
        o=[Meter("o",Decimal(0),Decimal(15),Decimal(1))]
        self.assertEqual(AquaFlowService().water_balance(i,o,Decimal(1)),Decimal(4))
    def test_solver(self):
        r=solve([Node("S",0,60),Node("A",5,None)],[Link("L","S","A",2)])
        self.assertTrue(r.converged)
    def test_lab_revision_chain(self):
        p={"sample":"S1","analyte":"lead","results":[
            {"sample":"S1","analyte":"lead","value":1.4,"revision":1},
            {"sample":"S1","analyte":"lead","value":1.2,"revision":2,"supersedes":1},
            {"sample":"S1","analyte":"lead","value":1.1,"revision":3,"supersedes":2},
            {"sample":"S2","analyte":"lead","value":9.9,"revision":1}]}
        r=AquaFlowService().run_workflow("lab_revision",p)
        self.assertEqual(r["decision"],"publish")
        self.assertEqual(r["value"],3)
        self.assertEqual(r["evidence"]["value"],1.1)
    def test_lab_revision_competing(self):
        p={"sample":"S1","analyte":"lead","results":[
            {"sample":"S1","analyte":"lead","value":1.4,"revision":1},
            {"sample":"S1","analyte":"lead","value":1.2,"revision":2,"supersedes":1},
            {"sample":"S1","analyte":"lead","value":1.3,"revision":3,"supersedes":1}]}
        with self.assertRaises(ValueError):AquaFlowService().run_workflow("lab_revision",p)
    def test_lab_revision_missing_predecessor(self):
        p={"sample":"S1","analyte":"lead","results":[
            {"sample":"S1","analyte":"lead","value":1.2,"revision":2,"supersedes":1}]}
        with self.assertRaises(ValueError):AquaFlowService().run_workflow("lab_revision",p)
    def test_lab_revision_current(self):
        rows=[Result("S1","lead",1.4,1),Result("S1","lead",1.1,2,1),Result("S2","lead",9.9,1)]
        r=current(rows,"S1","lead")
        self.assertEqual((r.revision,r.value),(2,1.1))
        with self.assertRaises(ValueError):current([Result("S1","lead",1.4,1),Result("S1","lead",1.2,2)],"S1","lead")
        with self.assertRaises(ValueError):current([Result("S1","lead",1.2,2,7)],"S1","lead")
if __name__=="__main__":unittest.main()
