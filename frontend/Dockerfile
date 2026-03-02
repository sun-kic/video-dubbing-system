FROM node:20-alpine

WORKDIR /app
COPY frontend/package.json /app/package.json
COPY frontend/tsconfig.json /app/tsconfig.json
COPY frontend/tsconfig.app.json /app/tsconfig.app.json
COPY frontend/tsconfig.node.json /app/tsconfig.node.json
COPY frontend/vite.config.ts /app/vite.config.ts
COPY frontend/index.html /app/index.html
COPY frontend/src /app/src

RUN npm install
EXPOSE 5173
CMD ["npm", "run", "dev"]
