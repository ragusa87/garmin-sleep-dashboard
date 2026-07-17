"""Moteur de conseils : règles indépendantes évaluées sur l'Analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .analysis import Analysis


@dataclass(frozen=True)
class Tip:
    id: str
    priority: int  # 1 = le plus important
    title: str
    body: str
    evidence: dict[str, str]


Rule = Callable[[Analysis], "Tip | None"]


def _fmt_h(hours: float) -> str:
    h = int(hours)
    m = round((hours - h) * 60)
    return f"{h} h {m:02d}"


def _offset_to_clock(offset_min: float) -> str:
    total = (offset_min + 18 * 60) % 1440
    return f"{int(total // 60):02d}:{int(total % 60):02d}"


def rule_short_sleep(a: Analysis) -> Tip | None:
    if a.avg_total_h_30d is None or a.avg_total_h_30d >= 7.0:
        return None
    return Tip(
        id="short_sleep",
        priority=1,
        title="Vous ne dormez pas assez",
        body=(
            "Votre durée moyenne de sommeil sur les 30 derniers jours est inférieure "
            "aux 7 à 9 heures recommandées pour un adulte. Le manque chronique de sommeil "
            "dégrade la récupération, la concentration et l'immunité. Visez une heure de "
            "coucher qui vous laisse au moins 7 h 30 au lit, en gardant la même heure de réveil."
        ),
        evidence={"Durée moyenne (30 j)": _fmt_h(a.avg_total_h_30d)},
    )


def rule_late_bedtime(a: Analysis) -> Tip | None:
    # offset 345 min = 23:45
    if a.median_bedtime_offset_min is None or a.median_bedtime_offset_min <= 345:
        return None
    return Tip(
        id="late_bedtime",
        priority=2,
        title="Couchez-vous plus tôt",
        body=(
            "Votre heure de coucher médiane est tardive. Se coucher après minuit réduit "
            "la part de sommeil profond (concentré en début de nuit) et souvent le REM par "
            "manque de durée totale. Avancez le coucher par paliers de 15 minutes ; instaurez "
            "un rituel sans écran 30 à 60 minutes avant."
        ),
        evidence={"Coucher médian": _offset_to_clock(a.median_bedtime_offset_min)},
    )


def rule_irregular_bedtime(a: Analysis) -> Tip | None:
    if a.bedtime_std_min is None or a.bedtime_std_min <= 45:
        return None
    return Tip(
        id="irregular_bedtime",
        priority=2,
        title="Régularisez vos heures de coucher",
        body=(
            "Vos heures de coucher varient beaucoup d'un jour à l'autre. La régularité est "
            "l'un des leviers les plus efficaces pour la qualité du sommeil : l'horloge interne "
            "anticipe l'endormissement et optimise les cycles. Fixez-vous une fenêtre de coucher "
            "de ± 30 minutes, week-end compris."
        ),
        evidence={"Écart-type du coucher": f"{a.bedtime_std_min:.0f} min"},
    )


def rule_low_deep(a: Analysis) -> Tip | None:
    if a.avg_deep_pct is None or a.avg_deep_pct >= 13:
        return None
    return Tip(
        id="low_deep",
        priority=3,
        title="Peu de sommeil profond",
        body=(
            "Votre part de sommeil profond est en dessous des 13 à 23 % typiques. Le sommeil "
            "profond pilote la récupération physique. Pour l'augmenter : de l'exercice "
            "d'endurance en journée (pas tard le soir), une chambre fraîche (17-19 °C), pas "
            "d'alcool le soir, et un coucher plus tôt — le profond domine le premier tiers de la nuit."
        ),
        evidence={"Sommeil profond moyen": f"{a.avg_deep_pct:.1f} %"},
    )


def rule_low_rem(a: Analysis) -> Tip | None:
    if a.avg_rem_pct is None or a.avg_rem_pct >= 18:
        return None
    return Tip(
        id="low_rem",
        priority=3,
        title="Peu de sommeil paradoxal (REM)",
        body=(
            "Votre part de sommeil REM est en dessous des 18 à 25 % typiques. Le REM, concentré "
            "en fin de nuit, soutient la mémoire et la régulation émotionnelle. Il est surtout "
            "amputé par un réveil trop tôt ou un coucher trop tard : allongez la nuit côté matin "
            "ou avancez le coucher, et évitez l'alcool qui supprime le REM."
        ),
        evidence={"REM moyen": f"{a.avg_rem_pct:.1f} %"},
    )


def rule_frequent_awakenings(a: Analysis) -> Tip | None:
    trigger_count = a.avg_awake_count is not None and a.avg_awake_count > 2
    trigger_pct = a.avg_awake_pct is not None and a.avg_awake_pct > 12
    if not (trigger_count or trigger_pct):
        return None
    ev = {}
    if a.avg_awake_count is not None:
        ev["Réveils par nuit"] = f"{a.avg_awake_count:.1f}"
    if a.avg_awake_pct is not None:
        ev["Temps éveillé au lit"] = f"{a.avg_awake_pct:.1f} %"
    return Tip(
        id="awakenings",
        priority=3,
        title="Nuits fragmentées",
        body=(
            "Vos nuits comportent beaucoup de réveils ou de temps éveillé. Pistes courantes : "
            "liquides ou alcool en soirée, chambre trop chaude ou bruyante, stress résiduel, "
            "repas tardif. Limitez les boissons 2 h avant le coucher et vérifiez l'environnement "
            "de la chambre (obscurité, silence, fraîcheur)."
        ),
        evidence=ev,
    )


def rule_low_spo2(a: Analysis) -> Tip | None:
    trigger_avg = a.avg_spo2 is not None and a.avg_spo2 < 92
    trigger_low = a.low_spo2_night_share is not None and a.low_spo2_night_share > 0.10
    if not (trigger_avg or trigger_low):
        return None
    ev = {}
    if a.avg_spo2 is not None:
        ev["SpO2 moyenne nocturne"] = f"{a.avg_spo2:.1f} %"
    if a.low_spo2_night_share is not None:
        ev["Nuits avec SpO2 < 85 %"] = f"{a.low_spo2_night_share * 100:.0f} %"
    return Tip(
        id="low_spo2",
        priority=1,
        title="Saturation en oxygène basse la nuit",
        body=(
            "Votre oxymétrie nocturne montre des valeurs basses répétées. Cela peut refléter "
            "une position de sommeil, une congestion… mais aussi une apnée du sommeil, surtout "
            "si vous ronflez ou êtes fatigué au réveil. Les capteurs au poignet sont imprécis, "
            "mais la récurrence justifie d'en parler à un médecin."
        ),
        evidence=ev,
    )


def rule_spo2_worsening(a: Analysis) -> Tip | None:
    if (
        a.spo2_low_share_recent is None
        or a.spo2_low_share_prev is None
        or a.spo2_n_recent < 8
        or a.spo2_n_prev < 8
    ):
        return None
    if a.spo2_low_share_recent - a.spo2_low_share_prev <= 0.15:
        return None
    return Tip(
        id="spo2_worsening",
        priority=1,
        title="Oxymétrie nocturne en dégradation",
        body=(
            "La part de nuits avec une désaturation sous 85 % a nettement augmenté sur les "
            "30 derniers jours par rapport aux 30 jours précédents. Si vous êtes traité pour "
            "une apnée du sommeil (PPC ou orthèse d'avancée mandibulaire), c'est le signal "
            "typique qui justifie un contrôle du réglage auprès de votre spécialiste — apportez "
            "ces chiffres en consultation. Sinon, parlez de ces désaturations récurrentes à un "
            "médecin. Rappel : le capteur au poignet est imprécis, c'est la tendance qui compte."
        ),
        evidence={
            "Nuits < 85 % (30 derniers j)": f"{a.spo2_low_share_recent * 100:.0f} % (n = {a.spo2_n_recent})",
            "Nuits < 85 % (30 j précédents)": f"{a.spo2_low_share_prev * 100:.0f} % (n = {a.spo2_n_prev})",
        },
    )


def rule_alcohol_like(a: Analysis) -> Tip | None:
    if a.elevated_hr_share is None or a.elevated_hr_share <= 0.15:
        return None
    return Tip(
        id="alcohol_like",
        priority=2,
        title="Fréquence cardiaque nocturne souvent élevée",
        body=(
            "Sur une part notable de vos nuits, la fréquence cardiaque pendant le sommeil "
            "dépasse nettement votre valeur de repos habituelle. Les causes classiques : alcool "
            "le soir, repas tardif et copieux, entraînement intense tardif, chaleur ou maladie. "
            "Si cela coïncide avec des verres en soirée, testez deux semaines sans alcool et "
            "comparez vos scores."
        ),
        evidence={
            "Nuits avec FC ≥ repos + 8 bpm": f"{a.elevated_hr_share * 100:.0f} %"
        },
    )


def rule_social_jetlag(a: Analysis) -> Tip | None:
    if a.social_jetlag_min is None or a.social_jetlag_min <= 60:
        return None
    return Tip(
        id="social_jetlag",
        priority=3,
        title="Jetlag social le week-end",
        body=(
            "Le milieu de votre nuit se décale nettement le week-end par rapport à la semaine — "
            "l'équivalent d'un petit décalage horaire hebdomadaire, qui rend les lundis difficiles. "
            "Limitez la grasse matinée à +1 h et gardez l'heure de coucher stable ; compensez "
            "plutôt par une sieste courte (20 min) en début d'après-midi."
        ),
        evidence={"Décalage week-end": f"{a.social_jetlag_min:.0f} min"},
    )


def rule_evening_stress(a: Analysis) -> Tip | None:
    high_stress = a.avg_sleep_stress is not None and a.avg_sleep_stress > 25
    corr = next(
        (
            c
            for c in a.correlations
            if c.variable == "avg_stress" and c.target == "score" and c.r is not None
        ),
        None,
    )
    stress_hurts = corr is not None and corr.r < -0.25
    if not (high_stress or stress_hurts):
        return None
    ev = {}
    if a.avg_sleep_stress is not None:
        ev["Stress moyen pendant le sommeil"] = f"{a.avg_sleep_stress:.0f} / 100"
    if stress_hurts:
        ev["Corrélation stress journée → score"] = f"r = {corr.r:.2f} (n = {corr.n})"
    return Tip(
        id="evening_stress",
        priority=2,
        title="Le stress pèse sur vos nuits",
        body=(
            "Votre niveau de stress mesuré pendant le sommeil est élevé, ou les journées "
            "stressantes se traduisent par de moins bons scores. Une routine de décompression "
            "aide : respiration lente ou cohérence cardiaque 10 minutes avant le coucher, "
            "écriture des tâches du lendemain pour « vider la tête », pas d'e-mails le soir."
        ),
        evidence=ev,
    )


def rule_activity_helps(a: Analysis) -> Tip | None:
    for var, label in (("steps", "pas"), ("intensity_min", "minutes intensives")):
        corr = next(
            (
                c
                for c in a.correlations
                if c.variable == var and c.target == "score" and c.r is not None
            ),
            None,
        )
        if corr is not None and corr.r > 0.25:
            return Tip(
                id="activity_helps",
                priority=4,
                title="Bougez : vos données le confirment",
                body=(
                    "Chez vous, les journées actives sont suivies de meilleures nuits — vos "
                    "propres données montrent une corrélation positive entre l'activité de la "
                    "journée et le score de sommeil. Maintenez une activité quotidienne, idéalement "
                    "terminée 3 h avant le coucher."
                ),
                evidence={f"Corrélation {label} → score": f"r = {corr.r:.2f} (n = {corr.n})"},
            )
    return None


# Textes français pour les enums Garmin les plus courants.
GARMIN_ENUM_FR = {
    "NEGATIVE_NOT_ENOUGH_REM": "pas assez de sommeil paradoxal (REM)",
    "NEGATIVE_NOT_ENOUGH_DEEP": "pas assez de sommeil profond",
    "NEGATIVE_LATE_BED_TIME": "heure de coucher tardive",
    "NEGATIVE_EARLY_WAKE_UP": "réveil trop matinal",
    "NEGATIVE_SHORT_SLEEP": "nuit trop courte",
    "NEGATIVE_SLEEP_DURATION": "durée de sommeil insuffisante",
    "NEGATIVE_RESTLESSNESS": "sommeil agité",
    "NEGATIVE_AWAKENINGS": "réveils fréquents",
    "NEGATIVE_STRESSFUL_SLEEP": "sommeil stressé",
    "NEGATIVE_LONG_AWAKE_TIME": "beaucoup de temps éveillé",
}


def rule_garmin_feedback(a: Analysis) -> Tip | None:
    frequent = {
        enum: freq
        for enum, freq in a.feedback_freq.items()
        if enum.startswith("NEGATIVE") and freq > 0.25
    }
    if not frequent:
        return None
    top = sorted(frequent.items(), key=lambda kv: -kv[1])[:3]
    ev = {}
    for enum, freq in top:
        label = GARMIN_ENUM_FR.get(enum, enum.replace("NEGATIVE_", "").replace("_", " ").lower())
        ev[label.capitalize()] = f"{freq * 100:.0f} % des nuits"
    return Tip(
        id="garmin_feedback",
        priority=4,
        title="Ce que Garmin vous répète",
        body=(
            "Certains verdicts négatifs reviennent sur plus d'un quart de vos nuits. "
            "Ce sont vos points faibles récurrents selon l'algorithme de la montre — "
            "les conseils ci-dessus s'attaquent aux mêmes causes."
        ),
        evidence=ev,
    )


RULES: tuple[Rule, ...] = (
    rule_short_sleep,
    rule_low_spo2,
    rule_spo2_worsening,
    rule_late_bedtime,
    rule_irregular_bedtime,
    rule_alcohol_like,
    rule_evening_stress,
    rule_low_deep,
    rule_low_rem,
    rule_frequent_awakenings,
    rule_social_jetlag,
    rule_activity_helps,
    rule_garmin_feedback,
)


def generate_tips(analysis: Analysis) -> list[Tip]:
    tips = [tip for rule in RULES if (tip := rule(analysis)) is not None]
    return sorted(tips, key=lambda t: t.priority)
