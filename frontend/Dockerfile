FROM node:24-slim

ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --registry="${NPM_CONFIG_REGISTRY}"

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
