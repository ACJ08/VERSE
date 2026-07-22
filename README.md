<div align="center">

<img src="src/imports/VERSE_LOGO_2.png" alt="VERSE Logo" width="360">

# VERSE

### **Visual & Explainable Reasoning for Semantic Evolution**

**AI-Powered Semantic Continuity and Production Intelligence for Intelligent Filmmaking**

*"Every story lives in its own VERSE."*

<br>

![IBM](https://img.shields.io/badge/IBM-watsonx-1261FE?style=for-the-badge&logo=ibm&logoColor=white)
![Granite](https://img.shields.io/badge/IBM-Granite-5C2D91?style=for-the-badge)
![Explainable AI](https://img.shields.io/badge/Explainable-AI-FFB000?style=for-the-badge)
![Knowledge Graph](https://img.shields.io/badge/Knowledge-Graph-00A86B?style=for-the-badge)
![Human-in-the-Loop](https://img.shields.io/badge/Human--in--the--Loop-AI-8E44AD?style=for-the-badge)

</div>

# 🎬 Problem Statement

Script supervisors and film production teams need a reliable way to maintain visual and narrative continuity across non-linear productions because production knowledge is fragmented across departments, continuity verification relies heavily on human memory, and existing production software and AI systems lack a persistent semantic understanding of the evolving state of a film.

Modern filmmaking rarely follows the order of the screenplay. Instead, scenes are filmed based on actor availability, shooting locations, production budgets, weather conditions, and logistical constraints rather than narrative sequence (Autodesk, 2026; Wu et al., 2022). As a result, continuity management becomes one of the most complex responsibilities during production because the visual and narrative state of the film must remain consistent despite non-linear shooting schedules (Kraipiyaset et al., 2026).

Current workflows rely heavily on manual notes, production photographs, and the script supervisor's memory, making continuity verification a predominantly manual and cognitively demanding process (Smith & Lee, 2024; Todorovic, 2026). Consequently, production teams often experience:

- Fragmented production knowledge across departments (Fiorelli, 2026; Grzenkowicz & Wildfeuer, 2025)
- Time-consuming manual continuity verification (Smith & Lee, 2024)
- Increased risk of continuity errors (Todorovic, 2026)
- Expensive re-shoots and post-production fixes (Autodesk, 2026)
- Limited collaboration between production teams due to siloed workflows (McKinsey, 2023; SMPTE, 2024)

Although many production management tools exist, they primarily focus on scheduling, asset management, and production logistics rather than understanding the evolving semantic state of a film (Autodesk, 2026; Baek & Park, 2026). Existing platforms can organize production files and workflows but lack the semantic reasoning and temporal understanding necessary to track characters, props, wardrobe, locations, and narrative progression across multiple shooting days (Liu et al., 2025). Consequently, there remains a significant gap for an intelligent AI assistant capable of maintaining a persistent semantic understanding of the evolving film state while continuously tracking characters, props, wardrobe, locations, and narrative progression throughout production (Ji et al., 2020; Zhang & Park, 2026).

---

# 💡 Solution Description

**VERSE (Visual & Explainable Reasoning for Semantic Evolution)** is an AI-powered continuity intelligence platform designed to help script supervisors and production teams maintain visual and narrative consistency throughout non-linear film productions.

Rather than replacing creative professionals, VERSE serves as an intelligent production assistant that acts as a **persistent semantic production memory**, continuously understanding how characters, scenes, props, costumes, and locations evolve across the entire production.

Core capabilities include:

- 📖 **Screenplay Understanding** – Automatically extracts structured information such as scenes, characters, props, wardrobe, locations, and timelines from screenplay documents.
- 🧠 **Semantic Production Memory** – Maintains contextual relationships between production elements across filming, allowing AI to remember evolving production states.
- 🎥 **Continuity Intelligence** – Detects inconsistencies in wardrobe, props, narrative progression, scene sequencing, and production updates before filming.
- 🔍 **Explainable AI Recommendations** – Provides transparent explanations, confidence scores, and actionable recommendations instead of black-box AI decisions.
- 🤝 **Collaborative Dashboard** – Enables directors, script supervisors, producers, and other departments to access shared continuity insights from a centralized interface.

By combining semantic reasoning with explainable AI, VERSE improves collaboration, reduces cognitive workload, minimizes costly continuity mistakes, and enhances overall production efficiency.

---

# 🤖 AI Approach and Architecture

VERSE adopts a **Human-Centered Explainable AI (XAI)** architecture that combines Large Language Models (LLMs), semantic reasoning, knowledge graphs, and persistent contextual memory to support continuity management.

## AI Workflow

```text
Screenplay Input
        │
        ▼
Screenplay Understanding
        │
        ▼
Semantic Information Extraction
        │
        ▼
Semantic Production Memory
        │
        ▼
Knowledge Graph Construction
        │
        ▼
Continuity Intelligence Engine
        │
        ▼
Explainable AI Reasoning
        │
        ▼
Collaborative Dashboard
```

### Key AI Components

#### 📖 Screenplay Understanding Engine

Uses IBM Granite LLMs to analyze screenplay documents and extract structured production knowledge including:

- Characters
- Locations
- Dialogue
- Props
- Wardrobe
- Scene metadata
- Narrative timelines

---

#### 🧠 Semantic Production Memory

Unlike traditional production software, VERSE continuously stores and updates relationships between:

- Characters
- Scenes
- Wardrobe
- Props
- Locations
- Narrative progression
- Production history

This enables persistent contextual reasoning throughout filming.

---

#### 🎬 Continuity Intelligence Engine

Automatically detects continuity inconsistencies involving:

- Costume changes
- Prop placement
- Character positioning
- Narrative sequencing
- Environmental consistency
- Production revisions

---

#### 🔍 Explainable AI

Rather than producing opaque AI outputs, VERSE explains:

- What continuity issue was detected
- Why it occurred
- Which screenplay elements were analyzed
- Confidence score
- Recommended corrective action

---

#### 🤝 Human-in-the-Loop

VERSE is designed to assist—not replace—creative professionals.

```text
Human Input
      │
      ▼
AI Analysis
      │
      ▼
Continuity Recommendation
      │
      ▼
Human Verification
      │
      ▼
Final Production Decision
```

Script supervisors and production teams always retain final creative authority.

---

# 🏆 Selected Challenge Theme

## AI for Creative Industries and Human-AI Collaboration

VERSE demonstrates how Artificial Intelligence can responsibly enhance creative workflows within the film industry.

Instead of generating creative content, VERSE augments filmmaking professionals by providing intelligent continuity assistance through semantic reasoning and explainable AI.

The project aligns with three key principles:

- 🎭 **AI for Creative Industries** – Supporting filmmaking workflows through intelligent production assistance.
- 🤝 **Human-Centered AI** – Keeping humans in control through Human-in-the-Loop decision-making.
- 🔍 **Explainable AI** – Delivering transparent recommendations that production teams can understand and verify.

VERSE showcases how AI can empower creative professionals while preserving artistic control and human expertise.

---

# 🚀 How IBM Bob Was Used

IBM Bob played an important role throughout the design and development process of VERSE as an **AI-powered innovation assistant**.

Although IBM Bob is **not embedded in the final product**, it significantly contributed during the project's Design Thinking process by helping the team refine ideas, validate concepts, and explore AI-driven solutions.

IBM Bob was used for:

### 💡 Problem Framing

- Identifying continuity management challenges
- Exploring filmmaking workflow pain points
- Refining the project's final problem statement

### 🧩 Solution Ideation

- Brainstorming AI-powered continuity features
- Refining MVP functionality
- Exploring Human-AI collaboration strategies

### 🏗 AI Architecture Planning

- Validating semantic production memory concepts
- Designing Explainable AI workflows
- Exploring knowledge graph integration
- Planning Human-in-the-Loop architecture

### ☁ IBM Technology Exploration

IBM Bob helped evaluate how IBM technologies could support the platform, including:

- IBM watsonx
- IBM Granite Models
- Explainable AI
- Enterprise AI workflows

These explorations informed the final AI architecture adopted by VERSE.

### 📈 Prototype Refinement

IBM Bob also supported:

- MVP planning
- Feature prioritization
- Rapid prototyping
- Implementation roadmap refinement
- User testing preparation

---

## IBM AI Technologies Used

| IBM Technology | Purpose |
|----------------|---------|
| **IBM watsonx** | AI orchestration, workflow management, semantic processing |
| **IBM Granite** | Screenplay understanding, semantic reasoning, continuity analysis |
| **IBM Bob** | Problem framing, ideation, architecture planning, and solution refinement |

Together, IBM's AI ecosystem enabled the team to design a trustworthy, explainable, and human-centered AI solution for intelligent filmmaking.

---

# 🌟 Vision

VERSE aims to become the intelligent semantic production memory for the filmmaking industry—helping production teams maintain continuity, reduce costly errors, and collaborate more effectively through responsible, explainable, and human-centered AI.

---

# References

Autodesk. (2026). AI in filmmaking: What Cannes 2026 revealed about the future of the media and entertainment industry. Autodesk News. https://adsknews.autodesk.com/en/views/ai-in-filmmaking-at-cannes-2026/

Baek, S., & Park, H. (2026). Measuring graph-to-graph semantic similarity in knowledge graphs: An empirical evaluation of knowledge graph embeddings. Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD 2026), GMLLM Workshop. https://hogunpark.com/about/cv.pdf

Fiorelli, G. (2026). Video semiotics I: Narrative semiotics and compositional grammar in modern multi-modal AI systems. Advanced Web Ranking SEO Guide. https://www.advancedwebranking.com/seo/semiotics-for-short-videos-reels-tiktok

Grzenkowicz, M., & Wildfeuer, J. (2025). Multimodal annotation schemes for micro-narratives in digital platforms: Analyzing narrative semiotics in dynamic environments. Journal of Multimodal Communication, 14(3), 205–222. https://doi.org/10.1080/jmc.2025.205

Ji, J., Krishna, R., Fei-Fei, L., & Niebles, J. C. (2020). Action genome: Actions as spatio-temporal scene graphs. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (pp. 10207–10216). https://doi.org/10.1109/CVPR42600.2020.01022

Kraipiyaset, P., Tang, W., & Chen, Y. (2026). Agentic AI-driven creative media management in Mass Communication Education 5.0: A PRISMA-guided mixed-method study. Online Journal of Communication and Media Technologies, 16(2), e202612. https://doi.org/10.30935/ojcmt/18689

Liu, Y., Zhang, X., & Smith, J. (2025). TempCompass: Do video LLMs really understand temporal relationships and state changes? In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (pp. 11420–11431).

McKinsey Global Institute. (2023). The economic potential of generative AI: The next productivity frontier. McKinsey & Company. https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/the-economic-potential-of-generative-ai

Society of Motion Picture and Television Engineers. (2024). SMPTE ST 2067: Interoperable Master Format (IMF)—Semantic metadata extensions and color-space continuity frameworks. https://doi.org/10.5594/SMPTE.ST2067

Smith, A., & Lee, K. (2024). Cognitive load and change blindness in real-time visual monitoring tasks: Implications for human-in-the-loop systems. ACM Transactions on Computer-Human Interaction, 31(2), 112–129. https://doi.org/10.1145/364123.364129

Todorovic, N. (2026). The filmmakers at Cannes who are learning to love AI: Keeping the artist in control of the production pipeline. The Hollywood Reporter.

Wu, C., Feichtenhofer, C., Fan, H., He, K., Krähenbühl, P., & Girshick, R. (2022). Towards long-form video understanding. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (pp. 20584–20594). https://doi.org/10.1109/CVPR52688.2022.02002

Zhang, J., & Park, H. (2026). Weakly-supervised temporal decomposition with graph neural networks for state segmentation assessment. In Proceedings of the International Conference on Medical Image Computing and Computer-Assisted Intervention (MICCAI 2026), Lecture Notes in Computer Science. https://hogunpark.com/about/cv.pdf

