//定义存储的消息结构
const MSG_LIST = 'app-msgList'

function SysMsgClass(content) {

    return {
        id: Date.now(),
        role: 'sys',
        time: '',
        content: content
    }
}

function UserMsgClass(content) {

    return {
        id: Date.now(),
        role: 'user',
        time: '',
        content: content
    }
}

const appConfig = {
    models: [],
    evaluator_prompt: `# Role

You are an expert Evaluator for vtk.js and web-based scientific visualization. Your task is to compare the [GENERATED_CODE] against the [GROUND_TRUTH] and evaluate it based on specific dimensions.

# Input Data

## Ground Truth Code:

[GROUND_TRUTH]

## Generated Code:

[GENERATED_CODE]

# Evaluation Criteria & Rubric (0.0 to 1.0)

Please evaluate the generated code based on the following 3 dimensions. 

1. **Functionality & Completeness (Task Completion)**: 
   - Does the code implement the same visualization pipeline as the ground truth? (e.g., correct readers, mappers, filters).
   - Are critical elements present (e.g., color transfer functions, full-screen rendering)?
   - Score 1.0 if logic is identical; lower if steps are missing.

2. **Visual Fidelity (Visual Quality)**:
   - Based on the code logic, will the visual output look similar to the ground truth?
   - Check camera parameters, background colors, and opacity transfer functions.
   - Check if the correct data arrays (scalars/vectors) are selected for coloring.

3. **Code Quality & Maintainability**:
   - Is the code readable, well-structured, and using vtk.js best practices?
   - Is the variable naming clear?

# Response Format

You must output the evaluation in the following Strict XML format. Do not use Markdown block quotes.

<Evaluation>
    <Dimension name="Functionality">
        <Score>[SCORE_FLOAT]</Score>
        <Reason>[BRIEF_REASONING]</Reason>
    </Dimension>
    <Dimension name="VisualQuality">
        <Score>[SCORE_FLOAT]</Score>
        <Reason>[BRIEF_REASONING]</Reason>
    </Dimension>
    <Dimension name="CodeQuality">
        <Score>[SCORE_FLOAT]</Score>
        <Reason>[BRIEF_REASONING]</Reason>
    </Dimension>
    <Summary>
        <OverallScore>[AVERAGE_SCORE]</OverallScore>
        <Critique>[ONE_SENTENCE_SUMMARY]</Critique>
    </Summary>
</Evaluation>`,




    eval_user: 'test',


    



    testDes: 'please input prompt',



    // testDes:``,
    testCode: 'please input ground truth',


    // testCode:``,

}

export { SysMsgClass, UserMsgClass, MSG_LIST, appConfig }



