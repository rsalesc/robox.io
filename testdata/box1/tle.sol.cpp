#include <bits/stdc++.h>

using namespace std;

int32_t main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n; cin >> n;

    vector<int> divisors;
    for(int i = 1; i <= n; i++) {
      if (n % i == 0) {
        divisors.push_back(i);
      }
    }

    sort(divisors.begin(), divisors.end());
    for (int x : divisors) cout << x << '\n';
    return 0;
}