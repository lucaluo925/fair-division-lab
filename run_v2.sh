#!/bin/zsh

cd ~/Desktop/fair-division-lab || exit

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

pip install -q streamlit numpy scipy pandas

streamlit run app_v2.py