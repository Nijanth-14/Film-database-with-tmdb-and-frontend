const fs = require('fs');
let content = fs.readFileSync('src/App.jsx', 'utf8');

content = content.replace(/text-google-black\/ hover:text-google-blue/g, 'text-google-black/60 hover:text-google-blue');
content = content.replace(/text-google-black\/ hover:text-google-red/g, 'text-google-black/60 hover:text-google-red');
content = content.replace(/text-google-black\/ hover:text-google-yellow/g, 'text-google-black/60 hover:text-google-yellow');
content = content.replace(/text-google-black\/ tracking-tight/g, 'text-google-black/90 tracking-tight');
content = content.replace(/text-google-black\/ bg-white\/5 px-2\.5/g, 'text-google-black/40 bg-white/5 px-2.5');
content = content.replace(/border-google-black\/">/g, 'border-google-black/10">');
content = content.replace(/text-google-black\/ group-focus-within/g, 'text-google-black/40 group-focus-within');
content = content.replace(/bg-white\/ hover:bg-white\/20/g, 'bg-white/40 hover:bg-white/20');
content = content.replace(/text-google-black\/ hover:text-white/g, 'text-google-black/80 hover:text-white');
content = content.replace(/text-google-black\/ font-medium flex-wrap/g, 'text-google-black/70 font-medium flex-wrap');
content = content.replace(/text-google-black\/ text-sm leading-relaxed/g, 'text-google-black/80 text-sm leading-relaxed');
content = content.replace(/text-google-black\/ space-y-2/g, 'text-google-black/60 space-y-2');
content = content.replace(/text-google-black\/ font-medium font-mono/g, 'text-google-black/60 font-medium font-mono');
content = content.replace(/text-google-black\/ mb-2/g, 'text-google-black/70 mb-2');
content = content.replace(/text-google-black\/ font-normal/g, 'text-google-black/40 font-normal');

// Special cases
content = content.replace(/<button onClick=\{onClose\} className="text-google-black\/80 hover:text-white transition-colors bg-white\/5 hover:bg-white\/10 p-2 rounded-full">/g, '<button onClick={onClose} className="text-google-black/50 hover:text-white transition-colors bg-white/5 hover:bg-white/10 p-2 rounded-full">');
content = content.replace(/text-google-black\/80 hover:bg-white\/5 hover:text-white border-l-2/g, 'text-google-black/70 hover:bg-white/5 hover:text-white border-l-2');

// Fix trailing slashes in components
content = content.replace(/text-google-black\/ /g, 'text-google-black/60 ');

fs.writeFileSync('src/App.jsx', content);
console.log('App.jsx fixed');
