"""Tramo sintético (datos inventados, de ninguna mina): RMR89, Q, GSI y Hoek-Brown.

La librería calcula y avisa; no recomienda sostenimiento. Interpretar es del ingeniero.
"""
import rockmasspy as rm


def main() -> dict:
    # RMR89: UCS 90 MPa, RQD 65, espaciado 0.25 m, JCond89 18, húmedo, orientación regular, túnel.
    inp = rm.Rmr89Input()
    inp.ucs_mpa = 90.0
    inp.rqd_pct = 65
    inp.spacing_m = 0.25
    inp.joint_condition_rating = 18
    inp.water = rm.Water.Damp
    inp.orientation = rm.OrientationClass.Fair
    r89 = rm.rmr89(inp)

    q = rm.q_value(rm.QInput(65, 9, 1.5, 2, 1, 1))
    gsi = rm.gsi_from_jcond89_rqd(18, 65)  # GSI cuantificado, no una correlación

    sigma_ci = 90.0
    p = rm.hb_params(gsi.gsi, 25, 0)  # mi = 25, D = 0, HB-2018 por defecto
    scm = rm.hb_global_strength(sigma_ci, p)
    s3max = rm.hb_sigma3max(scm, 0.027, 400, rm.HbApplication.Tunnel)  # MN/m3, m
    mc = rm.hb_mohr_coulomb(sigma_ci, p, s3max)
    erm = rm.erm_hoek_diederichs_simplified(gsi.gsi, 0)

    for nombre, valor, res in [
        ("RMR89", r89.rmr, r89), ("Q", q.q, q), ("GSI", gsi.gsi, gsi),
        ("phi' (deg)", mc.phi_deg, mc), ("c' (MPa)", mc.cohesion_mpa, mc), ("Erm (MPa)", erm.value, erm),
    ]:
        print(f"{nombre:11s} {valor:10.4f}  [{res.info.method_id}]  warnings: {list(getattr(res, 'warnings', []))}")

    return {"rmr89": r89.rmr, "q": q.q, "gsi": gsi.gsi, "phi_deg": mc.phi_deg,
            "cohesion_mpa": mc.cohesion_mpa, "erm_mpa": erm.value}


if __name__ == "__main__":
    main()
