# PlasticList Search

PlasticList Search is a demo search interface for the [PlasticList](https://www.plasticlist.org/) project, a research initiative that tested over 100 everyday foods from the Bay Area for the presence of plastic chemicals. The study, conducted by a team of independent researchers, quantified the levels of endocrine-disrupting chemicals (EDCs) and other plastic-related substances in common food items. The accompanying TSV dataset contains extensive data on chemical levels, testing conditions, and safety thresholds.

Access PlasticList Search [here](https://frontend-ten-lac-57.vercel.app/) to explore the comprehensive dataset and query detailed information about plastic chemicals in your favorite foods.

PlasticList Search is built with **Next.js 15** and **Material-UI** for a responsive frontend and leverages **FastAPI**, **Python**, and **Supabase** for the backend.

## Nice Features

- **Retrieval-Augmented Generation (RAG):** Utilizes the Voyage-3-Large model and Anthropic’s [embeddings](https://docs.anthropic.com/en/docs/build-with-claude/embeddings) for sophisticated context retrieval from relevant documents and TSV data.
  
- **Anthropic Tool Use:** Implements Anthropic's [tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) to run Python Pandas queries on the TSV dataset, enabling users to perform complex data manipulations and analyses directly through the search interface.

- **Persistent Conversation History:** Maintains a history of user interactions, allowing for seamless continuation of queries and discussions. Also supports automatically generated follow-up queries.

- **Code Boxes:** Provides code snippets and structured responses for better clarity and usability.

## License

This project is licensed under the MIT License.

## Notes

Some things I would have like to get done:

- better user experience, showcase of python code is bad sometimes
  - stream for tool use?
- just better prompting with more context. still doesn't feel great for complex queries.
- initial vision was to try implementing iterative tool use

## Acknowledgements

Special thanks to the independent research team behind PlasticList.
