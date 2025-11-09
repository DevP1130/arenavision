# ⚡ Fast Mode - Analysis Factors

When **Fast Mode** is enabled, the system uses **only Gemini Vision** (no Video Intelligence API) to analyze videos. Here's what factors it uses:

## 🔍 Frame Analysis (Gemini Vision)

For each sampled frame, Gemini Vision analyzes:

### 1. **Sport Detection**
- Identifies what sport is being played (basketball, soccer, football, etc.)

### 2. **Action Detection**
- Detects shot attempts (basketball)
- Detects goal attempts (soccer)
- Detects scoring plays
- Identifies any significant action

### 3. **Success Detection** ⭐ **Most Important**
- **SUCCESSFUL**: Made basket, goal scored, point scored
- **MISSED**: Ball missed, shot blocked, failed attempt
- **Only successful plays are marked as highlights**

### 4. **Player Visibility**
- Detects if a player is visible in the frame
- Identifies if player is preparing to shoot/score
- Used to extend segments to show the shooter (important for context)

### 5. **Crowd Reaction** (0-10 scale)
- Estimates excitement level:
  - **0-2**: Low/no reaction
  - **3-5**: Moderate reaction
  - **6-8**: High excitement
  - **9-10**: Very high excitement
- Higher crowd reaction = higher priority for highlights

### 6. **Highlight-Worthiness**
- Determines if the moment is highlight-worthy
- Based on success, action, and crowd reaction

## 📊 Frame Sampling Strategy

The number of frames analyzed depends on video length:

- **< 2 minutes**: 10 frames (sampled evenly throughout video)
- **2-5 minutes**: 20 frames
- **5-10 minutes**: 30 frames
- **> 10 minutes**: 40 frames

**Important**: Frames are sampled **evenly throughout the entire video**, not just the beginning.

## 🎯 Ranking Factors (Planner Agent)

After Gemini Vision detects events, the Planner Agent ranks them using:

### Scoring System:

1. **Base Confidence** (0.3-0.5)
   - Initial confidence from Gemini Vision detection

2. **Success Bonus** (+0.5) ⭐
   - Big boost for successful plays (made shots, goals)
   - This is the most important factor

3. **Ending Bonus** (+0.4)
   - Moments in the last 30 seconds get boosted
   - Ensures the ending is always included

4. **Crowd Reaction Bonus**
   - **High (7-10)**: +0.3
   - **Medium (5-6)**: +0.1
   - Higher excitement = higher priority

5. **Action Bonus** (+0.2)
   - Any frame with detected sports action

6. **Scoring Play Bonus** (+0.3)
   - Keywords: "goal", "touchdown", "dunk", "basket", "score", "made"
   - Only if not marked as "missed"

7. **Random Variation** (±0.05)
   - Small random factor to avoid identical results each run

### Filtering:

- **Skips**: Moments with **final score** < 0.2 (after all bonuses/penalties applied)
  - Note: Base confidence (0.3-0.5) + bonuses usually results in scores > 0.2
  - Only moments with negative penalties (missed shots, no action) might drop below 0.2
- **Penalizes**: Missed shots with low crowd reaction (-0.3)
- **Includes**: Almost everything else (very lenient)

## 🎬 What Gets Selected

The system prioritizes:

1. ✅ **Successful plays** (made shots, goals, scores)
2. ✅ **High crowd reaction** (excitement level 7+)
3. ✅ **Ending moments** (last 30 seconds)
4. ✅ **Any significant action** (even if not perfect)

The system **excludes**:
- ❌ Missed shots (unless crowd reaction is high)
- ❌ Low-quality moments (score < 0.2)
- ❌ Non-action frames

## 📈 Example Scoring

**High Priority Highlight:**
- Successful basket + High crowd reaction (8) + Near end of game
- Score: 0.5 (base) + 0.5 (success) + 0.3 (crowd) + 0.4 (ending) = **1.7**

**Medium Priority:**
- Successful play + Moderate crowd (5)
- Score: 0.5 (base) + 0.5 (success) + 0.1 (crowd) = **1.1**

**Low Priority (might be skipped):**
- Missed shot + Low crowd (2)
- Score: 0.3 (base) - 0.3 (missed) = **0.0** (skipped)

## 🔄 Variation

- **30% chance** to swap 2nd and 3rd place moments
- **±5% random variation** on all scores
- This ensures different highlights each run while keeping the best moments

## ⚡ Fast Mode Advantages

1. **Faster**: No Video Intelligence API (saves 1-3 minutes)
2. **Still Accurate**: Gemini Vision is very good at detecting successful plays
3. **Context-Aware**: Detects player visibility for better segment timing
4. **Crowd-Aware**: Uses crowd reaction to prioritize exciting moments

## 📝 Summary

**Fast Mode factors:**
- ✅ Success (made vs missed) - **Most Important**
- ✅ Crowd reaction (0-10)
- ✅ Player visibility
- ✅ Action presence
- ✅ Ending moments (last 30s)
- ✅ Random variation

The system is **very lenient** - it includes almost all moments with any action, but **prioritizes successful plays** heavily.

