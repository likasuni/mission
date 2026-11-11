#!/bin/zsh
# 열쇠 하나를 맥 키체인에 넣어요. 쓰는 법: _tools/auto/set_secret.sh COUPANG_ACCESS_KEY
# 값은 물어볼 때 붙여 넣어요 (글자 안 보임). 채팅에 붙여 넣지 마세요.
[[ -n ${1:-} ]] || { echo "사용법: $0 <열쇠 이름>"; exit 1; }
print -n "$1 값 (붙여 넣기, 글자는 안 보여요): "; read -rs V; echo
[[ -n $V ]] || { echo "값이 비었어요."; exit 1; }
security add-generic-password -U -s "likasuni-$1" -a "$USER" -w "$V" && echo "저장됨: $1 (${#V}글자)"
