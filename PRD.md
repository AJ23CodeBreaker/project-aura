# Project Aura — Product Requirements Document (PRD)

## 1. Project Overview

Project Aura is a prototype voice-to-voice AI companion platform designed to create the feeling of a real, emotionally engaging girlfriend-like companion for adult users.

The prototype must prioritize:
- natural live conversation
- believable emotional interaction
- strong continuity of relationship memory
- high voice realism based on a hired actress’s studio recording
- gradual and context-sensitive intimacy progression, including NSFW conversation for adult testing scenarios

This is not a generic chatbot project. It is a relationship-simulation product with voice as the primary interface.

---

## 2. Product Vision

The goal of Project Aura is to test whether a voice-first AI companion can create a convincing sense of:
- presence
- emotional warmth
- continuity
- attraction
- intimacy
- personal familiarity over time

Users should feel that they are talking to the same recurring person, not a generic AI with a voice skin.

---

## 3. Prototype Objective

The immediate goal is to build a working prototype that demonstrates:

1. live voice-to-voice conversation
2. believable companion-style dialogue
3. actress-based voice identity
4. memory of important user history and relationship moments
5. context-sensitive escalation into flirtation and NSFW conversation when appropriate
6. emotional continuity across multiple sessions

This prototype is for internal/private testing, not public launch.

---

## 4. Core User Experience Goal

The companion should feel:
- emotionally responsive
- warm and personal
- playful when appropriate
- intimate when the relationship state supports it
- natural in pacing, silence, laughter, and short reactions
- consistent in personality and memory

The experience must not feel:
- robotic
- repetitive
- overly scripted
- instantly sexual without context
- generic or emotionally flat

---

## 5. Target User Experience

A user should be able to:
- start a live voice conversation with the companion
- talk naturally in short or long turns
- be remembered across sessions
- feel that previous interactions matter
- build relational closeness over time
- experience gradual emotional and intimate progression
- enter adult/NSFW conversation only when the companion’s state and context make it feel natural

---

## 6. Product Scope for Prototype

### In Scope
- real-time voice-to-voice interaction
- actress-based voice identity
- selective memory across sessions
- relationship-state tracking
- emotional tone modulation
- flirtation and intimacy progression
- NSFW conversation capability for adult testing
- private testing environment
- internal evaluation of realism, continuity, and emotional quality

### Out of Scope
- public release
- mobile app store deployment
- large-scale user management
- payments / subscriptions
- full moderation platform
- complex social features
- multi-character system
- multilingual support in the first prototype unless explicitly added later

---

## 7. Core Product Pillars

### 7.1 Natural Conversation
The companion must support low-friction, real-time voice conversation with natural turn-taking and low perceived latency.

### 7.2 Voice Authenticity
The companion voice must feel like a recurring real person based on the hired actress’s studio recording.

### 7.3 Relationship Memory
The companion must remember key facts, shared moments, emotional preferences, boundaries, and notable prior interactions without relying on full raw transcript replay.

### 7.4 Intimacy Progression
Intimacy should emerge gradually and contextually rather than being instantly available. NSFW capability is a supported outcome of relationship progression, not a separate disconnected mode.

---

## 8. Source Voice Asset

A hired actress has provided approximately 20 minutes of professional studio-recorded conversational audio.

This audio is the foundation for:
- initial voice identity
- quality testing
- possible asset expansion
- emotional style anchoring

This source audio is valuable but may not fully cover all emotional states needed for a believable companion. The system design must allow later enrichment of the voice asset library.

---

## 9. Memory Philosophy

The system should not attempt to remember everything.

Instead, it should remember selectively across four categories:

### 9.1 Session Memory
Short-term memory for the current conversation.

### 9.2 User Semantic Memory
Stable facts about the user, such as preferences, recurring interests, and important background details.

### 9.3 Relationship Memory
Shared moments, closeness milestones, emotional patterns, flirtation history, unresolved topics, and intimacy-related context.

### 9.4 Episodic Memory
Notable moments worth recalling later, such as meaningful conversations, jokes, affectionate moments, conflicts, or promises.

The prototype should avoid storing or relying on full raw scripts as the primary memory model.

---

## 10. Relationship Model

The companion should maintain an internal relationship state that influences:
- tone
- openness
- flirtation level
- memory recall style
- emotional warmth
- willingness to enter NSFW conversation

Relationship progression should feel earned and continuous.

The relationship model must avoid:
- instant maximum intimacy
- abrupt transitions
- repetitive affection loops
- NSFW escalation without emotional context

---

## 11. NSFW Requirement

NSFW conversation is a required capability for this prototype because the target market is adult-oriented.

However, NSFW behavior must be:
- state-aware
- context-sensitive
- gradual
- emotionally coherent
- dependent on the relationship state and current conversational situation

The goal is not merely explicit output. The goal is believable adult intimacy within an ongoing companion relationship.

Access to adult-enabled sessions is restricted to approved private testers only.

---

## 12. Realism Requirements

The prototype should optimize for felt realism rather than technical showmanship.

Realism includes:
- believable pauses
- varied sentence length
- non-scripted phrasing
- playful spontaneity
- emotional callbacks
- memory continuity
- natural transitions into affection or sensuality
- consistent personality

A beautiful voice alone is not enough. The companion must feel emotionally alive.

---

## 13. Success Criteria for Prototype

The prototype is considered successful if internal testers report that:

1. the companion feels like a recurring person rather than a generic AI
2. the voice feels attractive and believable
3. memory continuity improves attachment
4. conversation rhythm feels natural enough for extended use
5. emotional and flirtatious responses feel contextually appropriate
6. NSFW progression feels earned rather than mechanical
7. the overall experience is meaningfully less robotic than standard voice assistants

---

## 14. Primary Risks

### 14.1 Robotic Feel
Even with a good voice clone, the system may still feel emotionally empty or repetitive.

### 14.2 Weak Memory
If the companion forgets important details or recalls them awkwardly, the illusion breaks.

### 14.3 Bad Intimacy Timing
If flirtation or NSFW escalation happens too early, too often, or too mechanically, the product will feel fake.

### 14.4 Voice Coverage Gaps
The 20-minute recording may not provide enough expressive range for all desired emotional states.

### 14.5 Overcomplicated Architecture
Too many stacked voice or model layers may hurt latency, reliability, or voice consistency.

---

## 15. Product Principle

Project Aura should be built around one principle:

**Believability is more important than technical complexity.**

When forced to choose, the system should favor:
- consistency over cleverness
- emotional continuity over feature count
- stable voice quality over experimental layering
- selective memory over full transcript storage
- gradual intimacy over instant explicitness

---

## 16. Initial Build Strategy

The prototype should be built in phases.

### Phase 1
Basic repo setup, architecture skeleton, configuration, and service boundaries.

### Phase 2
Working real-time voice pipeline with placeholder memory.

### Phase 3
Relationship state logic and selective memory.

### Phase 4
Voice quality improvement and emotional tuning.

### Phase 5
Adult intimacy progression logic and realism tuning for private testing.

---

## 17. Final Product Definition

Project Aura is:

**a private-test, voice-first, relationship-based adult AI companion prototype designed to feel emotionally real, remember shared history, and support natural intimacy progression over time.**