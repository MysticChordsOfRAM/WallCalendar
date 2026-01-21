FROM debian:trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-pyqt5 \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    git \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

CMD ["python3", "wall_calendar.py"]