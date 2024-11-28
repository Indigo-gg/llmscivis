Run ollama as the server mode

use

```
export OLLAMA_HOST=127.0.0.1:11435
```

to reset the port if the address is being used

using `ollama serve` to start the ollama by server mode.

Refer this doc for ollama api

```
https://github.com/ollama/ollama/blob/main/docs/api.md
```
Take some time to understand parameter specified in the `Parameters` section of readme.


## TODO List

Use the input parameter as a message for next response

Summarize task description-and code pair, such as open data, adding filters, adding control configurations, etc

If the code is not right, how to use LLM to solve it?
Using wrong code and output message from debugger, the right code as output for preparing the training data

Also put the propmt as a separate dialogue. (using `num_ctx` to control the length of context, modelfile https://github.com/ollama/ollama/blob/main/docs/modelfile.md#examples)

Connect to the better backend such as gpt4 or gpt4o

provide the editing function through the editor

Using better template as the prompt?

Using some data to do the fine tune? Start to collect the data, and make it similar to the Ds1000, maybe make the code fully correct is unreasonable, just train a debugger that can help to auto correct the code which can be helpful! Fine granularity trainning data set is important.

disable the cache when update contents

add the data upload section

add the voice input area

try vue (evey component per file)



### Other tips

[done] Store the context information? (two ways, using api/chat messages, using context of the api/generate, the generate is one time api, the api messages contains user->assistent user->assistent a serios of info)

ModelFile is a little bit to dockefile

Each time we use model file, and create associated information, we add several layers over it and get a new model

this is the exmaple we get, the model-file-one is the model we customized based on existing model

model-file-1:latest	9d7bc80d4e8e	4.7 GB	About a minute ago	
llava:latest       	8dd30f6b0cb1	4.7 GB	2 weeks ago       	
llama3:latest      	365c0bd3c000	4.7 GB	3 weeks ago  

Associated approach to limit the context size

https://github.com/ollama/ollama/blob/main/docs/faq.md

? differences between prompt and context?


Differences between context and prompt


In Ollama, the concepts of "context" and "prompt" are essential for understanding how interactions with AI models are structured and how information is processed. Here are the key differences between them:

Context:
Definition: The context in Ollama refers to the background information, prior interactions, or the setting in which the conversation is taking place. It is essentially the memory that the AI retains about the ongoing conversation or previous conversations.
Persistence: Context can be persistent across multiple interactions. It helps the AI maintain continuity in conversations, allowing it to refer back to previous statements, remember details about the user, or retain the thread of a discussion over time.
Usage: Context is used to give the AI a deeper understanding of the conversation history and user preferences, ensuring more coherent and relevant responses. It is particularly useful for long-term interactions or complex dialogues where maintaining a flow of information is crucial.
Prompt:
Definition: The prompt in Ollama refers to the immediate input given to the AI at a specific moment. It is the direct question, command, or statement that the user provides to initiate a response from the AI.
Immediate Interaction: Unlike context, a prompt is specific to the current interaction. It sets the stage for the AI's next response but does not inherently include the historical data unless explicitly mentioned within the prompt.
Usage: Prompts are used to guide the AI's responses in real-time, shaping the immediate output based on the latest user input. They can be questions, instructions, or any other form of direct communication.
Example to Illustrate:
Context:

User tells the AI in a previous session: "I love Italian food, especially pasta."
In a later session, the AI remembers this preference and incorporates it into responses, suggesting Italian restaurants or recipes without being explicitly reminded.
Prompt:

User in the current session: "What are some good Italian restaurants nearby?"
The AI responds based on this immediate input, providing a list of nearby Italian restaurants.
By differentiating between context and prompt, Ollama can create more nuanced and user-specific interactions, ensuring both immediate relevance and long-term coherence in conversations.


differences between chat api and generate api, look at this in detail
https://github.com/ollama/ollama/issues/2774

using chat api, not generate api


Ollam api page

https://llama-cpp-python.readthedocs.io/en/latest/api-reference/