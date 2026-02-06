FROM node:20-alpine AS build
WORKDIR /app
COPY tma/package.json /app/
RUN npm install --no-audit --no-fund
COPY tma /app
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
