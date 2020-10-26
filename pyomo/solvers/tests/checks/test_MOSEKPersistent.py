import pyutilib.th as unittest

from pyomo.opt import (TerminationCondition,
                       SolutionStatus,
                       SolverStatus)
import pyomo.environ as aml
import pyomo.kernel as pmo
import sys
from test_MOSEKDirect import *

try:
    import mosek
    mosek_available = True
    mosek_version = mosek.Env().getversion()
except ImportError:
    mosek_available = False
    modek_version = None

diff_tol = 1e-3

@unittest.skipIf(not mosek_available, "MOSEK's python bindings are missing.")
class MOSEKPersistentTests(unittest.TestCase):

    def setUp(self):
        self.stderr = sys.stderr
        sys.stderr = None

    def tearDown(self):
        sys.stderr = self.stderr

    def test_variable_removal(self):
        m = aml.ConcreteModel()
        m.x = aml.Var()
        m.y = aml.Var()
        opt = aml.SolverFactory('mosek_persistent')
        opt.set_instance(m)

        self.assertEqual(opt._solver_model.getnumvar(), 2)

        opt.remove_var(m.x)
        self.assertEqual(opt._solver_model.getnumvar(), 1)

        opt.remove_var(m.y)
        self.assertEqual(opt._solver_model.getnumvar(), 0)
        self.assertRaises(ValueError,opt.remove_var,m.x)

        opt.add_var(m.x)
        opt.add_var(m.y)
        self.assertEqual(opt._solver_model.getnumvar(), 2)
        opt.remove_vars(m.x, m.y)
        self.assertEqual(opt._solver_model.getnumvar(),0)

    def test_constraint_removal_1(self):
        m = aml.ConcreteModel()
        m.x = aml.Var()
        m.y = aml.Var()
        m.z = aml.Var()
        m.c1 = aml.Constraint(expr = 2*m.x >= m.y**2)
        m.c2 = aml.Constraint(expr = m.x**2 >= m.y**2 + m.z**2)
        m.c3 = aml.Constraint(expr = m.z >= 0)
        m.c4 = aml.Constraint(expr = m.x + m.y >= 0)
        opt = aml.SolverFactory('mosek_persistent')
        opt.set_instance(m)

        self.assertEqual(opt._solver_model.getnumcon(),4)
        
        opt.remove_constraint(m.c1)
        self.assertEqual(opt._solver_model.getnumcon(),3)

        opt.remove_constraints(m.c2, m.c3)
        self.assertEqual(opt._solver_model.getnumcon(),1)

        opt.add_constraint(m.c1)
        self.assertEqual(opt._solver_model.getnumcon(),2)
        self.assertRaises(ValueError,opt.remove_constraint,m.c2)
        
    def test_constraint_removal_2(self):
        m = pmo.block()
        m.x = pmo.variable()
        m.y = pmo.variable()
        m.z = pmo.variable()
        m.c1 = pmo.conic.rotated_quadratic.as_domain(2, m.x, [m.y])
        m.c2 = pmo.conic.quadratic(m.x, [m.y, m.z])
        m.c3 = pmo.constraint(m.z > 0)
        m.c4 = pmo.constraint(m.x + m.y > 0)
        opt = pmo.SolverFactory('mosek_persistent')
        opt.set_instance(m)

        self.assertEqual(opt._solver_model.getnumcon(),2)
        self.assertEqual(opt._solver_model.getnumcone(),2)
        
        opt.remove_constraint(m.c1)
        self.assertEqual(opt._solver_model.getnumcon(),2)
        self.assertEqual(opt._solver_model.getnumcone(),1)

        opt.remove_constraints(m.c2, m.c3)
        self.assertEqual(opt._solver_model.getnumcon(),1)
        self.assertEqual(opt._solver_model.getnumcone(),0)

        opt.add_constraint(m.c1)
        self.assertEqual(opt._solver_model.getnumcone(),1)
        self.assertRaises(ValueError,opt.remove_constraint,m.c2)

    def test_column_addition(self):
        '''
        Test based on lo1.py problem from MOSEK documentation.
        '''
        sol_to_get = [0.0, 0.0, 15.0, 8]

        m = aml.ConcreteModel()
        m.x = aml.Var(bounds = (0, None))
        m.y = aml.Var(bounds = (0, 10))
        m.z = aml.Var(bounds = (0, None))
        m.c1 = aml.Constraint(expr = 3*m.x + m.y + 2*m.z == 30)
        m.c2 = aml.Constraint(expr = 2*m.x + m.y + 3*m.z >= 15)
        m.c3 = aml.Constraint(expr = 2*m.y <= 25)
        m.o = aml.Objective(expr = 3*m.x + m.y + 5*m.z, sense= aml.maximize)
        opt = aml.SolverFactory('mosek_persistent')
        opt.set_instance(m)

        m.new_var = aml.Var(bounds = (0, None))
        opt.add_column(m, m.new_var, 1, [m.c2, m.c3], [1,3])

        self.assertEqual(opt._solver_model.getnumvar(), 4)
        self.assertEqual(len(opt._solver_model.getc()),4)

        opt.solve(m)
        for i,v in enumerate([m.x, m.y, m.z, m.new_var]):
            with self.subTest(i=v.name):
                self.assertAlmostEqual(v.value, sol_to_get[i], places = 0)

    
    def test_variable_update(self):
        '''
        Test based on milo1.py problem from MOSEK documentation.
        '''
        cont_sol_to_get = [1.948, 4.922]
        int_sol_to_get = [5,0]
        
        m = aml.ConcreteModel()
        m.x = aml.Var()
        m.y = aml.Var()
        m.c1 = aml.Constraint(expr = 50*m.x + 31*m.y <= 250)
        m.c2 = aml.Constraint(expr = 3*m.x - 2*m.y >= -4)
        m.o = aml.Objective(expr = m.x + 0.64*m.y, sense = aml.maximize)
        opt = aml.SolverFactory('mosek_persistent')
        opt.set_instance(m)
        opt.solve(m)

        self.assertAlmostEqual(m.x.value, cont_sol_to_get[0], places = 2)
        self.assertAlmostEqual(m.y.value, cont_sol_to_get[1], places = 2)

        m.x.setlb = 0
        m.x.setub = None
        m.x.domain = aml.Integers
        m.y.setlb = 0
        m.y.setub = None
        m.y.domain = aml.Integers
        m.z = aml.Var()

        opt.update_vars(m.x, m.y)
        self.assertRaises(ValueError, opt.update_var(m.z))
        opt.solve(m)
        self.assertAlmostEqual(m.x.value, int_sol_to_get[0], places = 1)
        self.assertAlmostEqual(m.y.value, int_sol_to_get[1], places = 1)

if __name__ == "__main__":
    unittest.main()