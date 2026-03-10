Move-Item frontend\src src_backup
Remove-Item frontend -Recurse -Force
npx create-vite@5 frontend --template react
Remove-Item frontend\src -Recurse -Force
Move-Item src_backup frontend\src
cd frontend
npm install
npm install axios recharts lucide-react
