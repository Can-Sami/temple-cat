# Minimal frontend Dockerfile to satisfy compose build contract
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
# Default start command for local development; override in compose if needed
CMD ["npm", "start"]
