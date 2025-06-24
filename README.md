# AI-Checkers
## Core Modules

- **Checkers_v24_original.py**  
  The baseline engine: board representation, move generator, game loop, and basic CLI interface. No AI—used to validate rules and move mechanics.

- **Checkers_v24_Heuristic_MiniMax_AlphaBeta_Pruning.py**  
  Builds on the original by adding a depth‐limited minimax search and alpha‐beta pruning. Implements a weighted heuristic (piece counts, king value, board control) for static position evaluation.

- **Checkers_v24_inference_system.py**  
  Wraps the search engine with inference‐based decision weighting: dynamically adjusts evaluation weights for multi‐jump sequences and game‐phase–specific strategies to improve tactical play.
