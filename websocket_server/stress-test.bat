FOR /L %%A IN (1,1,120) DO (
  start python relay.py --from-channel public --to-void
)