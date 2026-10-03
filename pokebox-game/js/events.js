// Pokebox — festivals: every day of the week one town holds its festival (like the films' town festivals).
// That town gets more Echoes of its festival types around it and a Festival Host in the plaza; beating the host once a day
// gives coins and a piece of clothing you can't otherwise pick. Purely date-based, so it works offline and on every device.
export const FESTIVALS = [
  { day: 0, town: 'mistvale', name: 'Firefly Night', types: ['Grass', 'Psychic'], color: '#c8ff9a', host: 'Lantern-keeper Ivy', line: 'The fireflies only dance for good Rangers. Show me!' },
  { day: 1, town: 'harbor', name: 'Wind Festival', types: ['Water', 'Colorless'], color: '#3d8fd6', host: 'Festival Host Mika', line: 'The wind is up — the whole harbour is out! Fancy a festival battle?' },
  { day: 2, town: 'voltspire', name: 'Storm Fair', types: ['Lightning', 'Metal'], color: '#ffd23c', host: 'Fair Captain Volt', line: 'Pylons at full power today. Your cards look charged — battle?' },
  { day: 3, town: 'starfall', name: 'Star Festival', types: ['Psychic', 'Metal'], color: '#ffd27a', host: 'Star-watcher Luma', line: 'Make a wish on the lanterns, then make a move!' },
  { day: 4, town: 'sandreach', name: 'Bazaar Day', types: ['Fighting', 'Fire'], color: '#e2683c', host: 'Bazaar Champion Rafa', line: 'Every stall is open and so am I. Best of three?' },
  { day: 5, town: 'frostline', name: 'Ice Gala', types: ['Water', 'Metal'], color: '#bfe3ff', host: 'Gala Skater Noor', line: 'One lap of the rink, one battle. That is the Gala rule!' },
  { day: 6, town: 'harbor', name: 'Market Weekend', types: ['Grass', 'Water'], color: '#5fae4f', host: 'Market Host Pell', line: 'Weekend market! Win and the stalls will remember your name.' },
];
export const festivalToday = (d = new Date()) => FESTIVALS.find(f => f.day === d.getDay()) || null;
export const festivalKey = (d = new Date()) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
