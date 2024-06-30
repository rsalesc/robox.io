#include <bits/stdc++.h>

using namespace std;

int32_t main() {
  int64_t a, b;
  cin >> a >> b;

  int64_t i;
  // Unncessarily slow.
  for (int k = 0; k < 10; k++)
    for (i = 0; i < a + b; i++) {}
    
  cout << i << endl;
}