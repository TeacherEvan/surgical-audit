# Convex Array Index + Mutation Matching

When a Convex schema uses `v.array(v.string())` for multi-value fields (e.g. `deviceIds`), the mutation and query must stay consistent.

## The bug pattern

Mutation accumulates:
```typescript
await ctx.db.patch(existing._id, {
  deviceIds: [...deviceIds, newId],  // array grows
});
```

Query uses exact array equality:
```typescript
.withIndex("by_deviceIds_category", (q) =>
  q.eq("deviceIds", [deviceId] as any)  // expects exact ["id"]
)
```

Once the array accumulates a second device (`["id1", "id2"]`), `.eq()` never matches — the query returns 0 even though data exists.

## The fix

Option A — mutation keeps array exact (replace, don't accumulate):
```typescript
await ctx.db.patch(existing._id, {
  ...data,
  deviceIds: [deviceId],  // exact replacement
});
```

Option B — query uses filter with array inclusion (`.includes()` or `.filter()` with array check) instead of `.eq()`.

Always verify: run mutation + query with the same `deviceId` and confirm the query returns the inserted record.
