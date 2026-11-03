#include <iostream>

using namespace std;

int main() {
    // Instead of a null pointer, let's create an actual integer variable
    int myNumber = 0;
    int* ptr = &myNumber;

    // Now we can safely store a value at the address ptr is pointing to
    *ptr = 10;

    cout << "The value is: " << *ptr << endl;

    return 0;
}