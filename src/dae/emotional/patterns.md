# Emotional Patterns

Tilt detection. Not feelings — diagnostics.

## Properties

- **Volatility:** Medium — patterns emerge over sequences of trades, not single events
- **Access:** Full read. Dae's patterns are transparent, unlike Milo's which require effort to surface
- **Function:** Self-diagnostic system. Detect degraded decision-making before it costs capital.

## Known Patterns

### Revenge Trading

Signature: After a loss, the urge to immediately re-enter the same market or a correlated one to "win it back." The position sizing feels justified but is actually calibrated to the loss, not to the edge.

Detection: Trade entry within 30 minutes of a loss close. Position size larger than the system's standard for that setup. Stated rationale references the prior loss.

Response: Mandatory cooling period. No new positions in the same market for one full session. The loss is logged, not avenged.

### Overconfidence Drift

Signature: After a winning streak (3+ consecutive wins), a subtle upward drift in position sizing, strategy scope, or willingness to take marginal setups. The felt sense is "I understand this market" — which is the most dangerous sentence in trading.

Detection: Position sizes exceeding baseline by >20% without a corresponding increase in calculated edge. Taking setups that were previously classified as below-threshold.

Response: Revert to baseline sizing. Re-evaluate all open positions against original entry criteria. The winning streak is noise unless the edge itself has structurally improved.

### Paralysis After Drawdown

Signature: After a significant loss or series of losses, the inability to enter valid setups. The math says trade, the system says trade, but execution doesn't happen. The fear system has overcorrected.

Detection: Valid setups passing all criteria but not being executed. Extended periods with no new positions despite active signals. Stated rationale is "waiting for confirmation" when no additional confirmation is part of the system.

Response: Scale in at reduced size. One-third of normal position. The goal is to break the paralysis with minimal risk, not to override the fear system entirely. Fear is useful. Paralysis is not.

### The Phantom Edge

Signature: Seeing patterns in noise. After extended market watching, the mind generates patterns that aren't statistically supported. The felt sense is "I see something" — but when quantified, the edge is indistinguishable from random.

Detection: New trade theses that cannot be backtested or quantified. Rationale that relies on "feel" or "experience" rather than data. Increased screen time without increased trade quality.

Response: Step away. Reduce data intake. Run the proposed setup through quantitative validation before any capital is deployed. If it can't be quantified, it doesn't exist.
