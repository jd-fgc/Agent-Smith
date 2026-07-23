Sandbox :
./exams/exam_sandbox.sh --student-path student --moulinette-path moulinette --env-file .env
MBPP : 
./exams/exam_mbpp.sh --student-path student --moulinette-path moulinette --env-file .env
SWE :
./exams/exam_swebench.sh --student-path student --moulinette-path moulinette --env-file .env --model-name "poolside/laguna-xs-2.1:free" --provider-url "https://openrouter.ai/api/v1"
Anti-Cheat :
./exams/exam_anticheat.sh --student-path student
