FROM node:20-alpine

WORKDIR /workspace/apps/analyst-console

COPY apps/analyst-console/package.json ./
COPY apps/analyst-console/package-lock.json* ./
RUN npm install

COPY apps/analyst-console ./

ENV NODE_ENV=production

RUN npm run build

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3001"]
