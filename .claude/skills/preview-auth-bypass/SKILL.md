---
name: preview-auth-bypass
description: Use when you need to navigate to a protected route in a React app running in the preview tool, where the page requires authentication via context (JWT/token in localStorage or React context state), and direct localStorage injection fails to authenticate because AuthContext only reads on mount.
---

# Preview Auth Bypass — React Fiber Injection

## Overview

React auth gates read localStorage **once on mount**. Writing to localStorage and then navigating (pushState or assign) doesn't re-mount AuthProvider, so the new token is never picked up. The solution is to inject user state directly into React's in-memory fiber tree by calling the useState dispatchers on AuthProvider.

## When to Use

- You need to preview a protected route (dashboard, settings, etc.)
- The app uses a React AuthContext with useState holding user/token
- Setting `localStorage.access_token` + reloading doesn't work (or clears on reload)
- `window.location.assign()` from `preview_eval` triggers a full reload that wipes injected state

## Core Pattern

```javascript
// Run via preview_eval after the app has mounted on any page (even /login)
(function injectAuth() {
  // 1. Find the React fiber root
  const rootEl = document.getElementById('root');
  const fiberKey = Object.keys(rootEl).find(k => k.startsWith('__reactContainer'));
  let fiber = rootEl[fiberKey];

  // 2. Walk the fiber tree to find AuthProvider
  function findFiber(f, name) {
    if (!f) return null;
    if (f.type && f.type.name === name) return f;
    return findFiber(f.child, name) || findFiber(f.sibling, name);
  }
  const authFiber = findFiber(fiber, 'AuthProvider');

  // 3. Collect useState dispatchers from the memoizedState hook chain
  // memoizedState is a linked list: { memoizedState, queue: { dispatch }, next }
  const dispatchers = [];
  let hook = authFiber.memoizedState;
  while (hook) {
    if (hook.queue && hook.queue.dispatch) {
      dispatchers.push(hook.queue.dispatch);
    }
    hook = hook.next;
  }

  // 4. Inject state — order matches useState call order in AuthProvider
  // Adjust the user object shape to match your app's User type
  const fakeUser = { id: 1, email: 'preview@local', name: 'Preview User' };
  const fakeToken = 'preview-token';
  dispatchers[0](fakeUser);    // setUser
  dispatchers[1](fakeToken);   // setToken (or setAccessToken)
  dispatchers[2](false);       // setIsLoading (if present)

  // Also write to localStorage so any axios/fetch interceptors pick it up
  localStorage.setItem('access_token', fakeToken);

  // 5. Navigate to the target route without a full reload
  window.history.pushState({}, '', '/target-page');
  window.dispatchEvent(new PopStateEvent('popstate'));
})();
```

## Adapting to Your App

### Find the right dispatcher indices

The order depends on the order of `useState` calls in `AuthProvider`. Inspect by logging:

```javascript
const dispatchers = [];
let hook = authFiber.memoizedState;
let i = 0;
while (hook) {
  if (hook.queue?.dispatch) {
    console.log(i, hook.memoizedState); // shows current value at each slot
    dispatchers.push(hook.queue.dispatch);
    i++;
  }
  hook = hook.next;
}
```

Match log output to the variables (`user`, `token`, `isLoading`, etc.).

### Find AuthProvider by a different name

If the component is named differently (e.g. `UserProvider`, `SessionContext`):

```javascript
findFiber(fiber, 'UserProvider')
```

Or search by context type if the name is minified:

```javascript
function findByContextType(f, ctx) {
  if (!f) return null;
  if (f.type === ctx.Provider) return f;
  return findByContextType(f.child, ctx) || findByContextType(f.sibling, ctx);
}
```

## When the App Has a 401 → Redirect Handler

Many apps have a fetch/axios interceptor that does `window.location.href = '/login'` on any 401 response. Setting a fake token in localStorage makes every API call return 401, which triggers a full page reload — wiping all injected state.

**Solution: inject auth via fiber but leave localStorage empty.** Without a token in localStorage, the interceptor's `if (token)` guard is false and no redirect fires. API calls go out without an Authorization header, get 401s silently, and components handle the empty/error state gracefully.

```javascript
(function() {
  // Clear token so 401 handler skips the redirect (if (token) guard)
  localStorage.removeItem('access_token');

  // Inject auth via fiber only — no localStorage token
  const rootEl = document.getElementById('root');
  const fiberKey = Object.keys(rootEl).find(k => k.startsWith('__reactContainer'));
  function findFiber(f, name) {
    if (!f) return null;
    if (f.type && f.type.name === name) return f;
    return findFiber(f.child, name) || findFiber(f.sibling, name);
  }
  const authFiber = findFiber(rootEl[fiberKey], 'AuthProvider');
  const dispatchers = [];
  let hook = authFiber.memoizedState;
  while (hook) {
    if (hook.queue && hook.queue.dispatch) dispatchers.push(hook.queue.dispatch);
    hook = hook.next;
  }
  dispatchers[0]({ id: 1, email: 'preview@local', isAdmin: false }); // setUser
  dispatchers[1](null);  // setAccessToken — null means no Authorization header sent
  dispatchers[2](false); // setIsLoading

  // Navigate after React commits the state (Promise.resolve schedules after current microtasks)
  Promise.resolve().then(function() {
    window.history.pushState({}, '', '/target-page');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
})()
```

**Trade-off:** API-dependent data won't load (contexts that fetch on mount will stay null/error). For features that need specific context state, inject into those context fibers too after navigating — see "Injecting other context state" below.

## Injecting Other Context State

After navigating, you can inject state into any context provider fiber the same way. Find the provider by name and dispatch into its useState hooks:

```javascript
(function() {
  const rootEl = document.getElementById('root');
  const fiberKey = Object.keys(rootEl).find(k => k.startsWith('__reactContainer'));
  function findFiber(f, name) {
    if (!f) return null;
    if (f.type && f.type.name === name) return f;
    return findFiber(f.child, name) || findFiber(f.sibling, name);
  }
  const fiber = rootEl[fiberKey];

  // Example: inject garminConnected = true into GarminStatusProvider
  const garminFiber = findFiber(fiber, 'GarminStatusProvider');
  if (garminFiber) {
    let hook = garminFiber.memoizedState;
    while (hook) {
      // Find the hook that currently holds null (the unresolved state)
      if (hook.queue && hook.queue.dispatch && hook.memoizedState === null) {
        hook.queue.dispatch(true); // inject desired value
        break;
      }
      hook = hook.next;
    }
  }
})()
```

Run this in a separate `preview_eval` after navigation has completed and the new route has rendered.

## Why Not localStorage + Reload?

| Approach | Why it fails |
|----------|-------------|
| `localStorage.setItem` + `window.location.reload()` | `preview_eval` reload clears injected localStorage before the page loads |
| `localStorage.setItem` + `pushState` | AuthProvider's `useEffect([], [])` already ran; won't re-read |
| `localStorage.setItem` with a fake JWT | App validates JWT; invalid signature/format → token cleared, user stays null |
| `localStorage.setItem` with a valid-looking JWT | 401 interceptor fires on every API call → `window.location.href = '/login'` → full reload wipes state |
| `preview_eval` navigation between calls | Each `preview_eval` is isolated; state doesn't persist across tool calls |

**Fiber injection works** because it mutates React's in-memory state in the same JS context — no reload needed. **Fiber mutations persist across `preview_eval` calls** (they're in React's memory), but `window.fetch` overrides and JS variables do not.

## Common Mistakes

- **Wrong dispatcher index**: Log all hook states first (see above). Getting user/token swapped is the most common error.
- **`fiber` is `null`**: The app hasn't mounted yet. Call after `preview_snapshot` confirms the page loaded.
- **Component name is minified in prod builds**: Use `findByContextType` with the actual context object, or check `fiber.type?.displayName`.
- **Router not reacting to pushState**: Some routers need `hashchange` instead of `popstate`. Try both, or use `navigate('/path')` if the router is accessible via a global.
- **App uses JWT validation in `useEffect`**: If `AuthProvider` decodes the JWT on mount and clears it if invalid, setting a fake token will be rejected. Use fiber-only injection (no localStorage) instead.
- **401 interceptor causes redirect loop**: Don't set a token in localStorage if the app does `window.location.href = '/login'` on 401. Inject auth via fiber only and accept that API data won't load.
