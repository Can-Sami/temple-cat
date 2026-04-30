1. Project Overview

The objective is to build and deploy a real-time Voice AI interface where a user can converse with an assistant possessing a dynamically configurable personality and behavior. The system must handle real-time state synchronization, voice orchestration, message roundtrip latency tracking, and robust deployment via Docker.  
2. Technology Stack

    Frontend: Next.js (latest) with TypeScript.  

    Frontend Data Fetching/State: TanStack Query (server cache). Minimal local state.  

    WebRTC Transport: Daily-js (Standard Pipecat transport for streaming audio).  

    Backend / Agent Framework: Python with Pipecat.  

    AI Services: Deepgram (STT), OpenAI (LLM), Cartesia (TTS).  

    Infrastructure: Docker Compose (single command docker compose up -d deployment), Cloudflare Tunnel (preferred) or ngrok for public URL exposure.  

    Target Environment: Single EC2 instance running Ubuntu 22.04 (e.g., t3.medium).  

3. Core Functional Requirements
3.1. Frontend Configuration Interface

Create a configuration panel (text areas/inputs) to set the following parameters before a session starts:  

    LLM Settings: System Prompt, Temperature, Max Tokens.  

    STT Settings: Temperature.  

    TTS Settings: Voice, Speed, Temperature.  

    Custom Setting: "Interruptibility Percentage" – This is a non-standard configuration that must be mapped to custom logic within the Pipecat pipeline.  

3.2. Voice Bot Backend (Pipecat)

    Pipeline Architecture: Construct a standard real-time pipeline: VAD → STT (Deepgram) → LLM (OpenAI) → TTS (Cartesia).  

    Dynamic Initialization: The agent must consume and react to the frontend configuration parameters (including the system prompt and interruptibility logic) upon session initialization.  

3.3. Real-Time Dashboard

While the session is active, the UI must display:

    Bot State Indicator: Visually distinguish between "Listening", "Thinking", and "Speaking".  

    Latency Metrics: Display the "Round Trip Latency" (calculated as the time from user silence to the start of the bot's audio response).  

3.4. Optional Add-on Selection

    Help Center (Qdrant RAG): Integrate the agent with Qdrant to perform recall on an artificial Q&A collection. Note for AI coding agent: Prioritize this add-on to establish a retrieval-augmented architecture for the voice bot.  

4. Non-Functional & Security Requirements

    Production Readiness: Implement reasonable error boundaries, logging mechanisms, rate-limiting, input validation, and retry logic.  

    Security: Implement basic CORS. Prevent injection vectors.  

    Secrets Management: Absolutely no secrets committed to git. Provide a .env.example file. The system must load actual keys (Deepgram, OpenAI, Cartesia) from a .env file or environment variables on the host machine.  

5. Testing Requirements

    Backend: Write focused unit tests for the Python/Pipecat logic.  

    Frontend: Write component and interaction tests for the Next.js UI.  

6. Deployment Strategy

    Containerization: The entire stack (frontend, backend, workers) must orchestrate via a single docker-compose.yml file.  

    Clean Boot: The application must successfully start from a clean box using only: git clone <repo> && cd <repo> && docker compose up -d. The compose file must work on the EC2 instance without modification.  

    Documentation: Provide a one-page DEPLOY.md detailing:

        Region, AMI, and instance type used.  

        Required open ports in the AWS Security Group.  

        Docker compose wiring explanation.  

        Log locations.  

        Restart procedures after a system reboot.  

7. Critical Evaluation Criteria

The implementation will be heavily judged on the following metrics. Ensure the architecture addresses these explicitly:  

    State Management: The UI must flawlessly and immediately reflect when the bot is interrupted by the user.  

    Framework Mastery (Pipecat): Proper implementation of InputParams or initialization routines to pass the custom system prompt and configuration from the frontend to the backend agent.  

    Code Hygiene: Clean, modular, and well-structured code.  

    Deployment Hygiene: The Docker setup must be flawless on a fresh EC2 instance, with sane logging and restart policies.