#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 17 07:48:41 2020

@author: yalinli_cabbi, joy_c
"""

import pandas as pd
import numpy as np
import os
import biosteam as bst
from thermosteam import Stream, utils
from sanitation import Components



__all__ = ('WasteStream',)

_defined_composite_vars = ('COD', 'BOD5', 'BOD', 'uBOD', 'C',
                           'N', 'P', 'K', 'Solids', 'Charge')

_specific_groups = {'SVFA': ('SAc', 'SProp'),
                    'XStor': ('XOHO_PHA', 'XGAO_PHA', 'XPAO_PHA', 
                              'XGAO_Gly', 'XPAO_Gly'),
                    'XANO': ('XAOO', 'XNOO'),
                    'XBio': ('XOHO', 'XAOO', 'XNOO', 'XAMO', 'XPAO', 
                             'XMEOLO', 'XACO', 'XHMO', 'XPRO'),
                    'SNOx': ('SNO2', 'SNO3'),
                    'XPAO_PP': ('XPAO_PP_Lo', 'XPAO_PP_Hi'),
                    'TKN': ()}

path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '_ratios.csv')
_default_ratios = pd.read_csv(path)
_default_ratios = dict(zip(_default_ratios.Variable, _default_ratios.Default))

del path

# %%

# =============================================================================
# Define the WasteStream class
# =============================================================================

@utils.registered(ticket_name='ws')
class WasteStream(Stream):
    '''A subclass of the Stream object in the thermosteam package with additional attributes and methods for waste treatment    '''
    
    _ratios = tuple(_default_ratios.keys())
    
    # TODO: add other state variables to initiation (pH, SAlk, SCAT, SAN)
    def __init__(self, ID='', flow=(), phase='l', T=298.15, P=101325.,
                 units='kg/hr', price=0., thermo=None, pH=7., SAlk=None,
                 **chemical_flows):
        
        super().__init__(ID=ID, flow=flow, phase=phase, T=T, P=P,
                         units=units, price=price, thermo=thermo, **chemical_flows)
        self._pH = pH
        self._SAlk = SAlk
        self._ratios = None
    
    def show(self, T=None, P=None, flow='kg/hr', composition=None, N=None,
             stream_info=True):
        '''Show WasteStream information'''        
        info = ''
        # Stream-related specifications
        if stream_info:
            super().show(T, P, flow, composition, N)
        else:
            info += self._basic_info()
            display_units = self.display_units
            T_units = T or display_units.T
            P_units = P or display_units.P
            info += self._info_phaseTP(self.phase, T_units, P_units)

         #!!! Need reviewing
#        info += self._component_info()
        
        #TODO: unit and definition for alkalinity
        # Component-related properties
        info += '\n WasteStream-specific properties:\n'
        info += f'  pH: {self._pH}\n'
        info += f'  Alkalinity: {self._SAlk} [unit]\n'
        
        print(info)
        
    _ipython_display_ = show
    
    # Component-related properties
    #!!! Need reviewing
#    def _component_info(self):
#        _ws_info = ''
#        _ws_info += '\n Component-specific properties:\n'
#        _ws_info += f'  TC      : {self.TC:.1f} g C/hr\n'
#        _ws_info += f'  TN      : {self.TN:.1f} g N/hr\n'
#        _ws_info += f'  TP      : {self.TP:.1f} g P/hr\n'
#        _ws_info += f'  TK      : {self.TK:.1f} g K/hr\n'
#        #!!! This display is definitely weired
#        _ws_info += f'  charge  : {self.charge:.1f} mol/hr\n'
#        _ws_info += f'  COD     : {self.COD:.1f} g O2/hr\n'
#        _ws_info += f'  BOD5    : {self.BOD5:.1f} g O2/hr\n'
#        _ws_info += f'  uBOD    : {self.uBOD:.1f} g O2/hr\n'
#        _ws_info += f'  Totmass : {self.Totmass:.1f} g/hr\n'
#        _ws_info += f'  Vmass   : {self.Vmass:.1f} g/hr\n'
#        return _ws_info
        
    @property
    def components(self):
        return self._thermo.chemicals

    @property
    def ratios(self):
        return self._ratios

    def composite(self, variable, subgroup=None, particle_size=None, 
                  degradability=None, organic=None, volatile=None,
                  specification=None):
        """
        calculate any composite variable by specifications

        Parameters
        ----------
        variable : str
            The composite variable to calculate. 
            One of ('COD', 'BOD5', 'BOD', 'uBOD', 'C', 'N', 'P', 'K', 'Solids', 'Charge').
        subgroup=None: CompiledComponents, optional
            A subgroup of CompiledComponents. The default is None.
        particle_size=None: 'g', 's', 'c', or 'x', optional 
            Dissolved gas ('g'), soluble ('s'), colloidal ('c'), particulate ('x'). 
            The default is None.
        degradability=None: 'b' or 'u', optional
            Either degradable ('b') or undegradable ('u'). The default is None.
        organic=None: bool, optional
            Organic (True) or inorganic (False). The default is None.
        volatile=None: bool, optional
            Volatile (True) or involatile (False). The default is None.
        specification=None: str, optional
            One of ('SVFA', 'XStor', 'XANO', 'XBio', 'SNOx', 'XPAO_PP','TKN'). 
            The default is None.


        Returns
        -------
        float
            The estimated value of the composite variable.

        """
        
        if variable not in _defined_composite_vars:
            raise KeyError(f"Undefined composite variable {variable}."
                           f"Must be one of {_defined_composite_vars}")            
        
        #!!! assuming it's a liquid WasteStream
        #TODO: deal with units
        if subgroup:
            cmps = subgroup
        else:
            cmps = self.components

        IDs = list(cmps.IDs)            
        if 'H2O' in IDs: IDs.remove('H2O')

        if specification:
            if specification == 'TKN': 
                IDs = [ID for ID in IDs if ID not in _specific_groups['SNOx']]
            elif specification not in _specific_groups.keys():
                raise KeyError(f"Undefined specification {specification}."
                               f"Must be one of _specific_groups.keys()."
                               f"Or, try defining 'subgroup'.")
            else: 
                IDs = [ID for ID in IDs if ID in _specific_groups[specification]]
                
        IDs = tuple(IDs)
        cmps = cmps.subgroup(IDs)
        cmp_c = self.imass[IDs]/self.ivol['H2O']*1e3      #[mg/L]
        
        if variable in ('COD', 'BOD5', 'BOD', 'uBOD'):
            if organic == False: var = 0.
            else: 
                organic = True
                if variable == 'COD': var = cmp_c
                elif variable == 'uBOD': var = cmps.f_uBOD_COD * cmp_c
                else: var = cmps.f_BOD5_COD * cmp_c
        elif variable == 'C':
            var = cmps.i_C * cmp_c
        elif variable == 'N':
            var = cmps.i_N * cmp_c
        elif variable == 'P':
            var = cmps.i_P * cmp_c
        elif variable == 'K':
            var = cmps.i_K * cmp_c
        elif variable == 'Solids':
            var = cmps.i_mass * cmp_c
            if volatile != None:
                if volatile: var *= cmps.f_Vmass_Totmass
                else: var *= 1-cmps.f_Vmass_Totmass
        else:
            var = cmps.i_charge * cmp_c
        
        dummy = np.ones(len(cmp_c))
        if particle_size:
            if particle_size == 'g': 
                dummy *= 1-getattr(cmps, 's')-getattr(cmps, 'c')-getattr(cmps, 'x')
            else:
                dummy *= getattr(cmps, particle_size)
        
        if degradability:
            if degradability == 'u': dummy *= 1-getattr(cmps, 'b')
            else: dummy *= getattr(cmps, 'b')
        
        if organic != None:
            if organic: dummy *= getattr(cmps, 'org')
            else: dummy *= 1-getattr(cmps, 'org')
        
        return sum(dummy*var)
    
    @property
    def COD(self):
        return self.composite('COD')

    @property    
    def BOD(self):
        return self.composite('BOD')
    
    @property
    def TC(self):
        return self.composite('C')
    
    @property
    def TOC(self):
        return self.composite('C', organic=True)
        
    @property
    def TN(self):
        return self.composite('N')
    
    @property
    def TKN(self):
        return self.composite('N', specification='TKN')
    
    @property
    def TP(self):
        return self.composite('P')
    
    @property
    def charge(self):
        return self.composite('Charge')
    
    def TDS(self, include_colloidal=True):
        TDS = self.composite('Solids', particle_size='s')
        if include_colloidal:
            TDS += self.composite('Solids', particle_size='c')
        return TDS
    
    def TSS(self, include_colloidal=False):
        TSS = self.composite('Solids', particle_size='x')
        if include_colloidal:
            TSS += self.composite('Solids', particle_size='c')        
        return TSS
    
    def VSS(self, include_colloidal=False):
        VSS = self.composite('Solids', particle_size='x', volatile=True)
        if include_colloidal:
            VSS += self.composite('Solids', particle_size='c', volatile=True)        
        return VSS        
    
    def ISS(self):
        return self.composite('Solids', particle_size='x', volatile=False)
    
    @classmethod
    def from_composite_measures(cls, ID, flow_tot=0., phase='l', T=298.15, P=101325., 
                                units=('L/hr', 'mg/L'), price=0., thermo=None, 
                                pH=7., SAlk=150., ratios=None, COD=430., TKN=40., TP=10., 
                                SNH4=25., SNO2=0., SNO3=0., SPO4=8., SCa=140., SMg=50., 
                                SK=28., XMeP=0., XMeOH=0., XMAP=0., XHAP=0., XHDP=0., 
                                XPAO_PP=0., DO=0., SH2=0., SN2=18., SCH4=0., SCAT=3., SAN=12.):
                
        cmps = Components.load_default()
        cmps.compile()
        bst.settings.set_thermo(cmps)
        
        cmp_dct = dict.fromkeys(cmps.IDs, 0.)
        if ratios:
            r = _set_ratios(ratios)
        else: r = _default_ratios

        #************ user-defined values **************        
        cmp_dct['SH2'] = SH2
        cmp_dct['SCH4'] = SCH4
        cmp_dct['SN2'] = SN2
        cmp_dct['SO2'] = DO
        cmp_dct['SNH4'] = SNH4
        cmp_dct['SNO2'] = SNO2
        cmp_dct['SNO3'] = SNO3
        cmp_dct['SPO4'] = SPO4
        cmp_dct['SCa'] = SCa
        cmp_dct['SMg'] = SMg
        cmp_dct['SK'] = SK
        cmp_dct['XMAP'] = XMAP
        cmp_dct['XHAP'] = XHAP
        cmp_dct['XHDP'] = XHDP
        cmp_dct['XMeP'] = XMeP
        cmp_dct['XMeOH'] = XMeOH
        cmp_dct['SCAT'] = SCAT
        cmp_dct['SAN'] = SAN
        
        #************ organic components **************
        cmp_dct['SCH3OH'] = COD * r['fSCH3OH_TotCOD']
        cmp_dct['SAc'] = COD * r['fSAc_TotCOD']
        cmp_dct['SProp'] = COD * r['fSProp_TotCOD']
        cmp_dct['SF'] = COD * r['fSF_TotCOD']
        cmp_dct['SU_Inf'] = COD * r['fSUInf_TotCOD']
        cmp_dct['SU_E'] = COD * r['fSUE_TotCOD']
        
        SOrg = sum([v for k,v in cmp_dct.items() if k in ('SCH3OH','SAc','SProp','SF','SU_Inf','SU_E')])
        
        XCU_Inf = COD * r['fXCUInf_TotCOD']
        cmp_dct['CU_Inf'] = XCU_Inf * r['fCUInf_XCUInf']
        cmp_dct['XU_Inf'] = XCU_Inf * (1 - r['fCUInf_XCUInf'])
        
        cmp_dct['XOHO'] = COD * r['fXOHO_TotCOD']
        cmp_dct['XAOO'] = COD * r['fXAOO_TotCOD']
        cmp_dct['XNOO'] = COD * r['fXNOO_TotCOD']
        cmp_dct['XAMO'] = COD * r['fXAMO_TotCOD']
        cmp_dct['XPAO'] = COD * r['fXPAO_TotCOD']
        cmp_dct['XACO'] = COD * r['fXACO_TotCOD']
        cmp_dct['XHMO'] = COD * r['fXHMO_TotCOD']
        cmp_dct['XPRO'] = COD * r['fXPRO_TotCOD']
        cmp_dct['XMEOLO'] = COD * r['fXMEOLO_TotCOD']
        
        XBio = sum([v for k,v in cmp_dct.items() if k.startswith('x') and k.endswith('O')])
        
        cmp_dct['XOHO_PHA'] = COD * r['fXOHOPHA_TotCOD']
        cmp_dct['XGAO_PHA'] = COD * r['fXGAOPHA_TotCOD']
        cmp_dct['XPAO_PHA'] = COD * r['fXPAOPHA_TotCOD']
        cmp_dct['XGAO_Gly'] = COD * r['fXGAOGly_TotCOD']
        cmp_dct['XPAO_Gly'] = COD * r['fXPAOGly_TotCOD']
        
        XStor = sum([v for k,v in cmp_dct.items() if k.endswith(('PHA','Gly'))])
        
        cmp_dct['XU_OHO_E'] = COD * r['fXUOHOE_TotCOD']
        cmp_dct['XU_PAO_E'] = COD * r['fXUPAOE_TotCOD']
        
        XU_E = cmp_dct['XU_OHO_E'] + cmp_dct['XU_PAO_E']
        
        XCB = COD - SOrg - XCU_Inf - XU_E
        CB = XCB * r['fCB_XCB']
        cmp_dct['CB_BAP'] = CB * r['fBAP_CB']
        cmp_dct['CB_UAP'] = CB * r['fUAP_CB']
        cmp_dct['CB_Subst'] = CB - cmp_dct['CB_BAP'] - cmp_dct['CB_UAP']
        
        cmp_dct['XB_Subst'] = XCB - CB - XBio - XStor
        
        cmp_c = np.asarray([v for v in cmp_dct.values()])
        VSS = (cmp_c * cmps.i_mass * cmps.f_Vmass_Totmass * cmps.x * cmps.org).sum()
        TSS = VSS/r['iVSS_TSS']
        XOrg_ISS = (cmp_c * cmps.i_mass * (1-cmps.f_Vmass_Totmass) * cmps.x * cmps.org).sum()

        del SOrg, XCU_Inf, XBio, XStor, XU_E, XCB, CB
        
        #************ inorganic components **************
        cmp_dct['XPAO_PP_Hi'] = XPAO_PP * r['fHi_XPAOPP']
        cmp_dct['XPAO_PP_Lo'] = XPAO_PP * (1 - r['fHi_XPAOPP'])
        
        ISS = TSS - VSS
        cmp_c = np.asarray([v for v in cmp_dct.values()])
        other_ig_iss = (cmp_c * cmps.i_mass * cmps.x * (1-cmps.org)).sum()
        cmp_dct['XIg_ISS'] = ISS - XOrg_ISS - other_ig_iss
        
        del ISS, VSS, TSS, XOrg_ISS, other_ig_iss, cmp_c
        
        # TODO: calibrate pH, SAlk, SCAT, SAN
        bad_vars = {k:v for k,v in cmp_dct.items() if v<0}
        if len(bad_vars) > 0:            
            raise ValueError(f"The following state variable(s) was found negative: {bad_vars}.")
        
        del bad_vars

        #************ calibrate XB_subst, SF's N, P content *************
        if SNH4 > 0 and cmp_dct['SF'] > 0:
            STKN = SNH4/r['fSNH4_STKN']
            cmp_c = np.asarray([v for v in cmp_dct.values()])
            SN = (cmp_c * cmps.i_N * cmps.s).sum()
            SF_N = cmp_dct['SF'] * cmps.SF.i_N
            SNOx_N = SNO2 * cmps.SNO2.i_N + SNO3 * cmps.SNO3.i_N
            other_stkn = SN - SF_N - SNOx_N - SN2*cmps.SN2.i_N
            SF_N = STKN - other_stkn
            
            if SF_N < 0:
                raise ValueError(f"negative N content for SF was estimated.")            
            
            cmps.SF.i_N = SF_N/cmp_dct['SF']
            
            del STKN, SN, SF_N, other_stkn
            
        other_tkn = (cmp_c*cmps.i_N).sum() - SNOx_N - SN2*cmps.SN2.i_N - cmp_dct['XB_Subst']*cmps.XB_Subst.i_N                
        XB_Subst_N = TKN - other_tkn
        if XB_Subst_N < 0:
            raise ValueError(f"negative N content for XB_Subst was estimated.")            
        cmps.XB_Subst.i_N = XB_Subst_N/cmp_dct['XB_Subst']
        
        other_p = (cmp_c*cmps.i_P).sum() - cmp_dct['XB_Subst']*cmps.XB_Subst.i_P
        XB_Subst_P = TP - other_p
        if XB_Subst_P < 0:
            raise ValueError(f"negative P content for XB_Subst was estimated.")    
        cmps.XB_Subst.i_P = XB_Subst_P/cmp_dct['XB_Subst']
        
        del other_tkn, XB_Subst_N, other_p, XB_Subst_P, cmp_c
        
        #************ convert concentrations to flow rates *************
        # TODO: other unit options
        cmp_dct = {k:v*flow_tot*1e-6 for k,v in cmp_dct.items()}       # [mg/L]*[L/hr]*1e-6[kg/mg] = [kg/hr]
        cmp_dct['H2O'] = flow_tot                                      # [L/hr]*1[kg/L] = [kg/hr]
        
        new = cls(ID=ID, phase=phase, T=T, P=P, units='kg/hr', price=price, 
                  thermo=thermo, pH=pH, SAlk=SAlk, **cmp_dct)
        new._ratios = r        
        return new

#%% FUNCTIONS

def _set_ratios(new_ratios):
    """allows user to specify ratios for composition characterization."""        
    r = _default_ratios
    for name, ratio in new_ratios.items():
        if name not in r.keys():
            raise ValueError(f"Cannot identify ratio named '{name}'."
                             f"Must be one of {r.keys()}")
        elif ratio > 1 or ratio < 0:
            raise ValueError(f"ratio {name}: {ratio} is out of range [0,1].")
        r[name] = ratio
    return r