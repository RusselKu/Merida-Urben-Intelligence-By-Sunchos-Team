# ==========================================================
# Mérida Urban Intelligence - Frontend Application Environment
# ==========================================================
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start Vite with external host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
