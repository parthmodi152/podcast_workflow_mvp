# React Admin UI Dockerfile
FROM node:16-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY ./src ./src
COPY ./public ./public

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["npm", "start"]
