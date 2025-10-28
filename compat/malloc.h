// Provide malloc.h compatibility on platforms where it's not present
#pragma once

#ifdef _WIN32
#  include <malloc.h>
#else
#  include <stdlib.h>
#endif

