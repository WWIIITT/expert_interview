# Slide-Aligned Video Summary

Source: `video.mp4`

Total slides: 18

## Slide 1 (00:00-00:18)

Slide content summary: Opening title slide introducing Dongwei Jiang’s presentation on the AAAI-2025 paper "Self-Incorrect: LRMs Struggle with Discriminating Self-Generated Responses," a joint work with colleagues at Johns Hopkins University. The speaker frames the talk as being about the self-improvement capability of large language models.

Speaker notes: The presenter introduces themselves, names the paper and collaborators, and states the talk’s focus on self-improvement in large models.

## Slide 2 (00:18-00:28)

Slide content summary: The speaker introduces the paper’s focus on the self-improvement capability of large language models and frames why the topic matters by noting concerns about AI self-improvement.

Speaker notes: This segment serves as the motivation for the talk. The speaker begins explaining the broader significance of self-improvement in AI and hints at common worries about what that capability could enable.

## Slide 3 (00:28-00:51)

Slide content summary: The slide presents the debate around AI self-improvement: some see it as a path to AI surpassing human intelligence and creating existential risk, while others view it as a promising goal for building stronger, safer models and enabling breakthroughs.

Speaker notes: The speaker contrasts concerns about AI exceeding human intelligence with the optimistic view that self-improvement could improve capability and safety at the same time. The interval ends by noting that this area has already attracted substantial research.

## Slide 4 (00:51-01:25)

Slide content summary: The slide discusses the challenge of improving LRMs while maintaining safety, and introduces a research debate about whether intrinsic self-improvement is possible. It contrasts claims that LRMs can improve themselves using only their own judgment with arguments that they still cannot self-improve without external feedback.

Speaker notes: The speaker frames this as an apparent contradiction in the literature: some researchers support intrinsic self-improvement, while others reject it as not yet achievable.

## Slide 5 (01:25-02:00)

Slide content summary: The speaker reframes a seeming contradiction in prior findings by splitting intrinsic self-improvement into two linked abilities: generation and discrimination. The slide motivates this decomposition with a human-growth analogy, emphasizing reflection and choosing better alternatives.

Speaker notes: The speaker argues that the apparent contradiction in earlier results motivates a new framing of intrinsic self-improvement. Instead of treating it as one capability, they separate it into generation and discrimination. They connect this idea to human development, where improvement comes from reflecting on actions and evaluating options, then choosing the best alternative over others.

## Slide 6 (02:00-02:25)

Slide content summary: The speaker argues that progress depends on choosing effectively among actions, ideas, and alternatives, and suggests this same ability to discriminate among options should also apply to LRMs. The segment ends by questioning whether that assumption is actually true.

Speaker notes: The narration frames decision quality as a core trait of growth: effective choices should outperform alternatives. It then connects this principle to LRMs as a proposed requirement, but closes with a skeptical question about whether the analogy holds.

## Slide 7 (02:25-03:12)

Slide content summary: The speaker explains that fair comparisons between generation and discrimination for LRMs are difficult because they are usually evaluated with different metrics. To solve this, the slide introduces an evaluation framework that enables sample-to-sample comparison of generation versus discrimination.

Speaker notes: The key point is that generation and discrimination are not normally measured on the same scale: generation uses metrics like ROG and related generation scores, while discrimination relies on classification metrics such as accuracy and F1. The speaker notes that Pyrowork compares these capabilities directly despite the metric mismatch, and the proposed framework is meant to make that comparison more principled by supporting sample-level evaluation.

## Slide 8 (03:12-04:35)

Slide content summary: Explains a fair comparison framework between generation and discrimination using the same sampled outputs. In generation, multiple answers are sampled with non-zero temperature, one is chosen at random, and evaluated with metric F such as exact match; performance is averaged across the dataset. In discrimination, the model sees the same samples, selects the best one via a prompt, and the chosen sample is evaluated with the same task metric; this performance is also averaged. The key point is that both modes use the same sample set, so they share the same upper and lower bounds, making the comparison fair and setting up the self-incorrect hypothesis.

Speaker notes: Emphasize that generation and discrimination are evaluated on identical sampled answers, which controls for sample quality and makes the comparison meaningful. The example highlights selecting sample 4 and scoring it with exact match. End by transitioning to the self-incorrect hypothesis.

## Slide 9 (04:35-05:22)

Slide content summary: The speaker defines a null hypothesis that LRMs are not reliably better at discriminating among previously generated alternatives than at generating initial responses, using `s_state`, `s_gen`, and `DGDIF` to frame the test. Because the same samples are used, the bounds are shared, and rejecting the hypothesis requires showing that `DGDIF` is sufficiently positive. The hypothesis is then evaluated across several mainstream LRMs and tasks.

Speaker notes: The slide introduces the self-incorrect null hypothesis (`H0`): LRMs do not reliably outperform themselves when choosing among prior alternatives compared with generating first-pass responses. The argument is grounded in comparing `s_state` and `s_gen`; `DGDIF` is defined via `s_gen`, and under `H0` it should be less than or equal to 0. The speaker emphasizes that, since the same samples are used, the upper and lower bounds are identical. The testing goal is to show a sufficiently large positive `DGDIF` to reject `H0`, and the evaluation spans multiple mainstream LRMs and tasks.

## Slide 10 (05:22-06:00)

Slide content summary: The speaker reports that experiments across several mainstream LRMs and tasks mostly support the hypothesis: DGDIF is usually small or negative, and the self-incorrect hypothesis is not rejected in 54 of 56 cases because p-values are above 0.05. The segment ends by raising the question of how these results scale.

Speaker notes: Emphasize the dominant pattern across experiments: blue bars vs. red bars show small or negative DGDIF, and statistical tests fail to reject the self-incorrect hypothesis in nearly all cases. Transition into the next topic by noting the open question about scaling behavior.

## Slide 11 (06:00-06:19)

Slide content summary: The speaker discusses whether model scale affects self-incorrect behavior, noting that DGDIF remains small or negative even for larger models, while stronger models show better discrimination with a larger DGDIF.

Speaker notes: This slide frames the scale question and highlights the key takeaway: increasing model size does not significantly increase self-incorrect, but it does improve discrimination.

## Slide 12 (06:19-06:42)

Slide content summary: The speaker transitions to the question of why discrimination is not easier than generation, and introduces a sub-hypothesis that autoregressive objectives may be relevant because their training process is more similar to generation. They also mention attempting to replicate experiments on FLAN-UL2 and FLAN-T5.

Speaker notes: Introduces the next research question and frames a hypothesis linking autoregressive training to generation. Mentions replication attempts on FLAN-UL2 and FLAN-T5.

## Slide 13 (06:42-07:02)

Slide content summary: The speaker reports replication experiments on FLAN-UL2 and FLAN-T5, noting that both non-purely autoregressive pretrained models show sufficiently large DGDIF values, which supports the proposed hypothesis before returning to the earlier contradiction.

Speaker notes: Key point: the observed large DGDIF for FLAN-UL2 and FLAN-T5 is presented as evidence supporting the hypothesis. The speaker then transitions back to addressing the contradiction discussed earlier.

## Slide 14 (07:02-07:18)

Slide content summary: The speaker revisits a contradiction in prior claims about LRMs self-improving, noting that some supporting papers depend on external feedback while the self-refine setup does not. To investigate, they say they replicated the self-refine experiments.

Speaker notes: Key point: the talk is narrowing in on whether self-improvement actually requires external feedback, motivating a replication of self-refine.

## Slide 15 (07:18-07:27)

Slide content summary: The speaker says they replicated the experiments using self-refine to investigate a contradiction and found an issue in the evaluation setup during replication.

Speaker notes: Replication of the experiments in self-refine revealed a problem with the evaluation setup, which may explain the contradiction.

## Slide 16 (07:27-09:36)

Slide content summary: The speaker highlights a flaw in the evaluation setup during replication: models can appear to improve by exploiting the task format rather than truly following feedback. In the constraint-generation example, the model mostly appends more sentences instead of rewriting to satisfy missing keywords, so the measured score can rise simply because longer text has a greater chance of including required terms.

Speaker notes: The key point is that self-refinement feedback may be too weak or low-level to drive real correction. Because the model keeps extending the paragraph, the number of satisfied constraints can increase even without genuine understanding, making it unclear whether observed gains reflect true task mastery or just chance.

## Slide 17 (09:36-11:32)

Slide content summary: The speaker concludes that the work finds no contradiction with prior research: if a model truly self-refined, it would strongly prefer refined outputs, but only a marginal preference is observed. They restate the paper’s motivation, framework, and main result that LRMs are not reliably better at discriminating among prior alternatives than at generating initial responses, while emphasizing the claim is limited to intrinsic self-improvement. The speaker also notes limitations and open questions, including broader evaluation across more models and tasks, uncertainty about true answer preferences, and whether fine-tuning can improve discrimination without harming generation.

Speaker notes: Closing remarks that connect the findings to the prior self-improvement debate, summarize the paper’s generation-vs-discrimination framework and main conclusion, and briefly mention limitations and future research directions.

## Slide 18 (11:32-11:35)

Slide content summary: Closing slide where the speaker ends the presentation and thanks the audience for listening.

Speaker notes: The speaker signals the end of the talk with a brief thank-you and no additional content.
