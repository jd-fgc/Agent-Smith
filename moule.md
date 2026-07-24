Sandbox :
./exams/exam_sandbox.sh --student-path student --moulinette-path moulinette --env-file .env
MBPP : 
./exams/exam_mbpp.sh --student-path student --moulinette-path moulinette --env-file .env --model-name "nvidia/nemotron-3-super-120b-a12b:free" --provider-url "https://openrouter.ai/api/v1"
SWE :
./exams/exam_swebench.sh --student-path student --moulinette-path moulinette --env-file .env --model-name "nvidia/nemotron-3-super-120b-a12b:free" --provider-url "https://openrouter.ai/api/v1"
Anti-Cheat :
./exams/exam_anticheat.sh --student-path student
