export const sheetMotion = {
  initial: { opacity: 0, y: 24, scale: 0.97 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 12, scale: 0.98 },
  transition: { type: 'spring', stiffness: 310, damping: 29, mass: 0.85, opacity: { duration: 0.18 } },
};
