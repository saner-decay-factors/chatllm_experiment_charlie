# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
_State clearly what you are trying to achieve and the architectural constraints, avoiding implementation specifics of HOW to do it. Focus on WHAT and WHY._

Feature: Chat sections with automatic title in a lateral bar

Just like we have for gemini and chatgpt,the goal of this task is to implement chat sections with automatic title using a lateral bar.

User should be able to create and change between sections using said sidebar.

Each section should hold it's history.

If the section does not have a title, it should be defined automatically based on the context as soon as the model gives its first answer.

Nothing else should be changed in the program unless it's affected by the sidebar.

## Steps
- [ ] understand the project and what is its current state
- [ ] identify how the screens are rendered (is there a sidebar already?)
- [ ] create (or update) the side bar component with the requested feature
- [ ] include automatic tests for visual renderization
- [ ] include automatic tests for the workflow of the project

## Success Looks Like
- [ ] there is a sibe bar with all chat sections
- [ ] the chat sections are being stored as they happened
- [ ] the chat sections are given an automatic title
- [ ] user is able to create new sections
- [ ] user is able to walk around the sections and navigate through them

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
