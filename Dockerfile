FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libegl1-mesa \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxi6 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "wall_calendar.py"]