#include "testlib.h"

using namespace std;

int main(int argc, char *argv[]) {
    setName("custom checker");
    registerTestlibCmd(argc, argv);

    quitf(_wa, "wrong answer");
    quitf(_pe, "presentation error");
    quitf(_ok, "ok");

    inf, ouf, ans;

    inf.readInt();
    inf.readInts(5);
    inf.readWord();
    inf.readDouble();
    inf.readLong();
}