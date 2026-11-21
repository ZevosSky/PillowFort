# Branch workflow for the tutorial

The same written lessons are available on `main`, `start` and
`reference-main`; their source trees serve different purposes. This checkout
is `main`. The guide contains 55 written chapters; 44, 56 and the
reflection lesson remain planned and are not missing prerequisites.

| Checkout | What to do here |
| --- | --- |
| `start` | Begin Chapter 01 and assemble the growing renderer in your own working branch. The initial scaffold deliberately lacks the later engine. It does carry some of the files the chapters supply rather than have you type: the scripts and test scenes under `Assets/`, and the CPU tests of Chapters 53, 54, 55 and 57 in `Tests/TutorialHarness/`, whose projects each chapter has you add. Chapter 57's, `DeclaredFrameTests.cpp`, comes with `UploadFailureTests.cpp`, the stand-ins for Vulkan's entry points that it includes. |
| `main` | Read the guide and maintain the project scaffold. Its source tree is not the assembled solution for every lesson. Use `start` for a clean tutorial beginning. |
| `reference-main` | Compare the assembled renderer, read its verification evidence, and prepare the named source exercises. Later features in this tree are not code to paste into an earlier stage. |

Keep your learning checkout and your reference checkout separate. Changing
the branch of a dirty learning checkout is not a prerequisite for a lesson.

## Building the growing chapter code

Follow the chapter's file-placement and build instructions in your learning
checkout. Source-file paths printed in listings describe files you create as
you progress. They need not exist in the initial scaffold. Basic graphics
and linear algebra are assumed; the guide's Vulkan and project conventions
still apply.

Chapter and image links in these copies stay local. Where a lesson points to a
source, test or verification-status file of the assembled reference tree (the
`reference-main` branch), it names the file by its path from that tree's root,
in code font and with no link: `Tests/TutorialHarness/README.md`, for example.
An assembled source file can include later changes; use the stated
chapter-stage listing or prepared exercise for your attempt.

## Prepared reference exercises

Commands using `Tests/TutorialHarness/Stages/Invoke-LearningStage.ps1`,
`Tests/TutorialHarness/Checkpoints/Invoke-SourceCheckpoint.ps1` or the named
native regression targets require the support on `reference-main`. The
scaffold's older harness is not interchangeable with those runners.

From a parent directory, create a separate authorized reference checkout:

```powershell
git clone --branch reference-main https://github.com/ZevosSky/PillowFort-private.git PillowFort-reference
Set-Location ./PillowFort-reference
git submodule update --init --recursive
```

Run a lesson's preparation commands from that reference checkout's root.
After preparation, edit and build its named Starter under
`Build/LearningStages/` or the exported CPU-checkpoint path the runner reports.
Keep the protected acceptance code unchanged. Running the solved root binary
does not test an edit made in the Starter.

The manual listings and prepared current-reference exercises are different
routes. A reference exercise supplies named later support; it does not prove
that every intermediate historical chapter listing was independently built.

## Reference access and public main

The working repository and reference history are private. The reference files
a lesson names, paired source exercises and their recorded evidence require
authorized access to that repository. The public `main` mirror contains the guide and scaffold,
not the private reference branch or its build receipts. A missing private
resource is an access or checkout issue, not a reason to count an unrun check
as passing. Publication continues through the existing private-main mirror;
these documentation updates do not merge the reference engine into `main`.
